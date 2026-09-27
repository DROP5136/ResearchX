"""LangGraph multi-agent research workflow (Phase 2 evidence-grounded)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from agents.analyst import AnalystAgent
from agents.extractor import ExtractorAgent
from agents.fact_checker import FactCheckerAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.writer import WriterAgent
from config import Settings, get_settings
from utils.instrumentation import timed_stage
from graph.state import ResearchState
from providers.llm import get_llm_provider
from providers.llm.base import LLMProvider
from schemas.claim import is_reportable_claim
from schemas.research import PipelineStatus, ResearchQuery, ResearchTask, TaskStatus
from schemas.source import Source
from storage.local_store import LocalStore
from tools.web_search import WebSearchTool
from utils.helpers import research_id as make_research_id
from utils.logging import get_logger

logger = get_logger("researchx.graph")


class ResearchWorkflow:
    """Orchestrates Planner → Research → Extract → FactCheck → Analyst → Writer."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMProvider | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ):
        self.settings = settings or get_settings()
        self.llm = llm or get_llm_provider(self.settings)
        self.search = WebSearchTool(settings=self.settings)
        self.planner = PlannerAgent(self.llm)
        self.researcher = ResearchAgent(self.llm, search=self.search, settings=self.settings)
        self.extractor = ExtractorAgent(self.llm)
        self.fact_checker = FactCheckerAgent(self.llm)
        self.analyst = AnalystAgent(self.llm)
        self.writer = WriterAgent(self.llm)
        self.progress_callback = progress_callback
        self._graph = self._build_graph()

    def _emit(self, message: str) -> None:
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    def _build_graph(self):
        graph = StateGraph(ResearchState)
        graph.add_node("planner", self._node_planner)
        graph.add_node("research", self._node_research)
        graph.add_node("extract", self._node_extract)
        graph.add_node("fact_check", self._node_fact_check)
        graph.add_node("additional_research", self._node_additional_research)
        graph.add_node("analyst", self._node_analyst)
        graph.add_node("writer", self._node_writer)
        graph.add_node("save", self._node_save)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "research")
        graph.add_edge("research", "extract")
        graph.add_edge("extract", "fact_check")
        graph.add_conditional_edges(
            "fact_check",
            self._route_after_fact_check,
            {
                "additional_research": "additional_research",
                "analyst": "analyst",
            },
        )
        graph.add_edge("additional_research", "extract")
        graph.add_edge("analyst", "writer")
        graph.add_edge("writer", "save")
        graph.add_edge("save", END)
        return graph.compile()

    def run(self, query: ResearchQuery, research_id: str | None = None) -> ResearchState:
        rid = research_id or make_research_id()
        initial: ResearchState = {
            "research_id": rid,
            "query": query,
            "plan": None,
            "tasks": [],
            "follow_up_tasks": [],
            "sources": [],
            "evidence": [],
            "claims": [],
            "claim_reviews": [],
            "contradictions": [],
            "datapoints": [],
            "dataset": None,
            "analysis": [],
            "report": None,
            "iteration": 0,
            "max_iterations": self.settings.max_research_iterations,
            "need_more_research": False,
            "sufficiency_reasons": [],
            "completed_with_limitations": False,
            "status": PipelineStatus.INIT,
            "errors": [],
            "progress": [],
            "pdf_document_ids": [],
            "meta": {},
        }
        if query.pdf_paths:
            try:
                from rag.pipeline import DocumentRAGPipeline

                rag = DocumentRAGPipeline(settings=self.settings)
                pdf_sources = rag.ingest_and_retrieve(query.pdf_paths, query.query)
                initial["sources"] = pdf_sources
                initial["pdf_document_ids"] = [
                    s.metadata.get("document_id", "") for s in pdf_sources if s.metadata
                ]
                self._emit(f"[Research] Ingested {len(pdf_sources)} PDF-derived sources")
            except Exception as exc:  # noqa: BLE001
                logger.warning("PDF RAG skipped: %s", exc)
                initial["errors"] = [f"PDF RAG error: {exc}"]

        result = self._graph.invoke(initial)
        return result  # type: ignore[return-value]

    # ── Nodes ──────────────────────────────────────────────────────────

    def _node_planner(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[1/7] Creating research plan...")

        def _run():
            plan = self.planner.plan(state["query"], research_id=state["research_id"])
            self._emit(f"[Planner] Created {len(plan.subtasks)} tasks")
            return {
                "plan": plan,
                "tasks": plan.subtasks,
                "status": PipelineStatus.PLANNING,
                "progress": ["planner_done"],
                "meta": dict(state.get("meta") or {}),
            }

        return timed_stage(state.get("meta") or {}, "planner", _run, items=1)

    def _node_research(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[2/7] Researching sources...")

        def _run():
            tasks = list(state.get("follow_up_tasks") or []) or list(state.get("tasks") or [])
            query = state["query"].query
            rid = state["research_id"]
            existing = list(state.get("sources") or [])
            all_sources: list[Source] = []
            max_workers = min(self.settings.max_concurrent_agents, max(1, len(tasks)))

            def _run_task(task: ResearchTask):
                self._emit(f"[Research] Task {task.task_id} started")
                srcs = self.researcher.research(task, query, research_id=rid)
                self._emit(f"[Research] Task {task.task_id} found {len(srcs)} sources")
                return srcs

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(_run_task, t) for t in tasks]
                for fut in as_completed(futures):
                    try:
                        all_sources.extend(fut.result())
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Parallel research task failed: %s", exc)

            merged = self._dedupe_sources(existing + all_sources)
            merged.sort(key=lambda s: s.quality_score, reverse=True)
            merged = merged[: self.settings.max_sources]
            self._emit(f"[Research] Collected {len(merged)} sources total")
            return {
                "sources": merged,
                "follow_up_tasks": [],
                "status": PipelineStatus.RESEARCHING,
                "progress": (state.get("progress") or []) + ["research_done"],
                "meta": dict(state.get("meta") or {}),
            }

        n_tasks = len(list(state.get("follow_up_tasks") or []) or list(state.get("tasks") or []))
        return timed_stage(state.get("meta") or {}, "research", _run, items=n_tasks)

    def _node_extract(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[3/7] Extracting evidence...")

        def _run():
            sources = self._dedupe_sources(state.get("sources") or [])
            claimed_sources = {sid for c in (state.get("claims") or []) for sid in c.source_ids}
            to_extract = [s for s in sources if s.source_id not in claimed_sources] or sources
            # On follow-up iterations, prefer newly added sources
            if state.get("iteration", 0) > 0 and claimed_sources:
                new_only = [s for s in sources if s.source_id not in claimed_sources]
                if new_only:
                    to_extract = new_only

            claims, evidence = self.extractor.extract_from_sources(
                to_extract,
                state["query"].query,
                research_id=state["research_id"],
            )
            existing_claims = state.get("claims") or []
            existing_evidence = state.get("evidence") or []
            seen = {c.claim.strip().lower() for c in existing_claims}
            new_claims = []
            for c in claims:
                key = c.claim.strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                new_claims.append(c)
            merged_claims = existing_claims + new_claims
            keep_eids = {eid for c in merged_claims for eid in c.evidence_ids}
            merged_evidence = [e for e in (existing_evidence + evidence) if e.evidence_id in keep_eids]
            if not merged_evidence and evidence:
                merged_evidence = existing_evidence + evidence
            self._emit(f"[Extraction] {len(merged_claims)} claims extracted")
            return {
                "sources": sources,
                "claims": merged_claims,
                "evidence": merged_evidence,
                "status": PipelineStatus.EXTRACTING,
                "progress": (state.get("progress") or []) + ["extract_done"],
                "meta": dict(state.get("meta") or {}),
            }

        return timed_stage(
            state.get("meta") or {},
            "extract",
            _run,
            items=len(state.get("sources") or []),
        )

    def _node_fact_check(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[4/7] Fact checking...")

        def _run():
            iteration = int(state.get("iteration") or 0)
            max_iterations = int(state.get("max_iterations") or self.settings.max_research_iterations)
            claims, contradictions, reviews, sufficiency = self.fact_checker.check(
                state.get("claims") or [],
                self._dedupe_sources(state.get("sources") or []),
                evidence_list=state.get("evidence") or [],
                plan=state.get("plan"),
                iteration=iteration,
                max_iterations=max_iterations,
                research_id=state["research_id"],
            )

            need_more = not sufficiency.is_sufficient
            completed_with_limitations = False
            if need_more and iteration >= max_iterations:
                need_more = False
                completed_with_limitations = True
                self._emit(
                    f"[ResearchLoop] Max iterations ({max_iterations}) reached — "
                    "COMPLETED_WITH_LIMITATIONS"
                )
            elif need_more:
                self._emit("[ResearchLoop] Additional research required")
                for reason in sufficiency.reasons:
                    self._emit(f"[ResearchLoop] Reason: {reason}")
            else:
                self._emit("[ResearchLoop] Evidence sufficient → Analyst")

            return {
                "claims": claims,
                "contradictions": contradictions,
                "claim_reviews": reviews,
                "need_more_research": need_more,
                "sufficiency_reasons": sufficiency.reasons,
                "follow_up_tasks": sufficiency.follow_up_tasks if need_more else [],
                "completed_with_limitations": completed_with_limitations
                or bool(state.get("completed_with_limitations")),
                "status": PipelineStatus.FACT_CHECKING,
                "progress": (state.get("progress") or []) + ["fact_check_done"],
                "meta": {
                    **(state.get("meta") or {}),
                    "sufficiency_stats": sufficiency.stats,
                },
            }

        return timed_stage(
            state.get("meta") or {},
            "fact_check",
            _run,
            items=len(state.get("claims") or []),
        )

    def _route_after_fact_check(self, state: ResearchState) -> str:
        max_iterations = int(state.get("max_iterations") or self.settings.max_research_iterations)
        if state.get("need_more_research") and int(state.get("iteration") or 0) < max_iterations:
            return "additional_research"
        return "analyst"

    def _node_additional_research(self, state: ResearchState) -> dict[str, Any]:
        iteration = int(state.get("iteration") or 0) + 1
        self._emit(f"[ResearchLoop] Iteration {iteration}")
        query = state["query"].query
        follow_ups = list(state.get("follow_up_tasks") or [])
        tasks = follow_ups or list(state.get("tasks") or [])[:2]

        extra_sources: list[Source] = []
        for task in tasks:
            task.search_queries = []
            task.status = TaskStatus.PENDING
            task.notes = task.notes or "additional_research"
            try:
                self._emit(f"[Research] Follow-up {task.task_id} started")
                found = self.researcher.research(task, query, research_id=state["research_id"])
                self._emit(f"[Research] Follow-up {task.task_id} found {len(found)} sources")
                extra_sources.extend(found)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Additional research failed: %s", exc)

        merged = self._dedupe_sources((state.get("sources") or []) + extra_sources)
        return {
            "sources": merged,
            "iteration": iteration,
            "need_more_research": False,
            "follow_up_tasks": [],
            "status": PipelineStatus.NEED_MORE_RESEARCH,
            "progress": (state.get("progress") or []) + ["additional_research_done"],
        }

    def _node_analyst(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[5/7] Running analysis...")

        def _run():
            analysis, datapoints, dataset = self.analyst.analyze(
                state.get("claims") or [],
                state["query"].query,
                research_id=state["research_id"],
            )
            ok_n = sum(1 for a in analysis if a.status == "ok")
            self._emit(f"[Analyst] {ok_n} metrics calculated ({len(datapoints)} datapoints)")
            return {
                "analysis": analysis,
                "datapoints": datapoints,
                "dataset": dataset,
                "status": PipelineStatus.ANALYZING,
                "progress": (state.get("progress") or []) + ["analyst_done"],
                "meta": dict(state.get("meta") or {}),
            }

        return timed_stage(
            state.get("meta") or {},
            "analyst",
            _run,
            items=len(state.get("claims") or []),
        )

    def _node_writer(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[6/7] Generating report...")

        def _run():
            sources = self._dedupe_sources(state.get("sources") or [])
            reportable = [
                c for c in (state.get("claims") or []) if is_reportable_claim(c.verification_status)
            ]
            completed_with_limitations = bool(state.get("completed_with_limitations")) or (
                len(reportable) < 2
            )
            limitations = [
                "Search coverage depends on free search providers and page accessibility.",
                "Source quality scores are prioritization heuristics, not truth labels.",
                f"Research iterations used: {state.get('iteration', 0)} / "
                f"{state.get('max_iterations', self.settings.max_research_iterations)}",
            ]
            for reason in state.get("sufficiency_reasons") or []:
                if "sufficient" not in reason.lower():
                    limitations.append(reason)

            report = self.writer.write(
                research_id=state["research_id"],
                query=state["query"].query,
                claims=state.get("claims") or [],
                sources=sources,
                contradictions=state.get("contradictions") or [],
                analysis=state.get("analysis") or [],
                evidence=state.get("evidence") or [],
                limitations=limitations,
                completed_with_limitations=completed_with_limitations,
            )
            self._emit("[Writer] Report generated")
            return {
                "report": report,
                "sources": sources,
                "completed_with_limitations": completed_with_limitations,
                "status": PipelineStatus.WRITING,
                "progress": (state.get("progress") or []) + ["writer_done"],
                "meta": dict(state.get("meta") or {}),
            }

        return timed_stage(state.get("meta") or {}, "writer", _run, items=1)

    def _node_save(self, state: ResearchState) -> dict[str, Any]:
        self._emit("[7/7] Saving results...")
        report = state.get("report")
        sources = self._dedupe_sources(state.get("sources") or [])
        store = LocalStore(state["research_id"])
        out_dir = store.save_run(
            report_md=report.markdown if report else "",
            report_json=report.model_dump() if report else {},
            sources=[s.model_dump(mode="json") for s in sources],
            evidence=[e.model_dump(mode="json") for e in (state.get("evidence") or [])],
            claims=[c.model_dump(mode="json") for c in (state.get("claims") or [])],
            contradictions=[c.model_dump(mode="json") for c in (state.get("contradictions") or [])],
            analysis=[a.model_dump(mode="json") for a in (state.get("analysis") or [])],
            datapoints=[d.model_dump(mode="json") for d in (state.get("datapoints") or [])],
            dataset=(state.get("dataset").model_dump(mode="json") if state.get("dataset") else None),
        )
        final_status = (
            PipelineStatus.COMPLETED_WITH_LIMITATIONS
            if state.get("completed_with_limitations")
            else PipelineStatus.COMPLETED
        )
        if not (state.get("claims") or []) and not sources:
            final_status = PipelineStatus.INSUFFICIENT_EVIDENCE

        self._emit(f"Research completed ({final_status.value}).\nOutput:\n{out_dir / 'report.md'}")
        return {
            "status": final_status,
            "meta": {**(state.get("meta") or {}), "output_dir": str(out_dir)},
            "progress": (state.get("progress") or []) + ["save_done"],
        }

    @staticmethod
    def _dedupe_sources(sources: list[Source]) -> list[Source]:
        seen: set[str] = set()
        unique: list[Source] = []
        for s in sources:
            key = (s.url or s.source_id).rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        return unique
