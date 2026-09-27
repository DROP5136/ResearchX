"""Thin orchestration service around ResearchWorkflow + LocalStore."""

from __future__ import annotations

import copy
import re
import threading
from typing import Any

from app.config import Settings, get_settings
from app.api.errors import APIError, PipelineFailureError, ResearchNotFoundError
from app.api.schemas.research import ResearchCreateRequest
from app.graph.workflow import ResearchWorkflow
from app.schemas.research import ResearchDepth, ResearchQuery
from app.storage.local_store import LocalStore
from app.utils.helpers import research_id as make_research_id
from app.utils.helpers import utc_now
from app.utils.logging import get_logger

logger = get_logger("researchx.api.research")

# Approximate stage progress for status polling (not real-time telemetry)
STAGE_PROGRESS: dict[str, int] = {
    "queued": 0,
    "planning": 10,
    "researching": 30,
    "extracting_evidence": 45,
    "fact_checking": 60,
    "additional_research": 55,
    "analyzing": 75,
    "writing": 90,
    "completed": 100,
    "failed": 100,
}


def _map_progress_message(message: str) -> tuple[str, int]:
    text = (message or "").lower()
    if "plan" in text:
        return "planning", STAGE_PROGRESS["planning"]
    if "additional" in text or "researchloop" in text or "follow-up" in text:
        return "additional_research", STAGE_PROGRESS["additional_research"]
    if "research" in text and "extract" not in text:
        return "researching", STAGE_PROGRESS["researching"]
    if "extract" in text:
        return "extracting_evidence", STAGE_PROGRESS["extracting_evidence"]
    if "fact" in text:
        return "fact_checking", STAGE_PROGRESS["fact_checking"]
    if "analy" in text:
        return "analyzing", STAGE_PROGRESS["analyzing"]
    if "writer" in text or "report" in text or "generating" in text:
        return "writing", STAGE_PROGRESS["writing"]
    if "sav" in text or "completed" in text:
        return "completed", STAGE_PROGRESS["completed"]
    return "researching", STAGE_PROGRESS["researching"]


def _sanitize_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Strip secrets and absolute filesystem paths from metadata returned to clients."""
    if not meta:
        return {}
    out = copy.deepcopy(meta)
    out.pop("output_dir", None)
    # Drop any values that look like absolute Windows/Unix paths
    for key, value in list(out.items()):
        if isinstance(value, str) and (
            value.startswith("/") or re.match(r"^[A-Za-z]:\\", value) or "\\" in value and ":" in value[:3]
        ):
            out.pop(key, None)
        if key.lower() in {"api_key", "token", "secret", "password"}:
            out.pop(key, None)
    return out


def _public_source(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    # Never expose absolute filesystem paths
    safe_meta = {
        k: v
        for k, v in meta.items()
        if k not in {"path"} and not (isinstance(v, str) and (":\\" in v or v.startswith("/")))
    }
    return {
        "source_id": row.get("source_id", ""),
        "title": row.get("title", ""),
        "url": row.get("url", "") if not str(row.get("url", "")).startswith("file:") else "",
        "domain": row.get("domain", ""),
        "published_at": row.get("published_at"),
        "source_type": row.get("source_type"),
        "relevance_score": row.get("relevance_score"),
        "quality_score": row.get("quality_score"),
        "authority_score": row.get("authority_score"),
        "snippet": (row.get("snippet") or "")[:500],
        "metadata": safe_meta,
    }


class ResearchService:
    """Orchestrates background research jobs using the existing pipeline."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}

    def start_research(self, body: ResearchCreateRequest) -> dict[str, str]:
        rid = make_research_id()
        store = LocalStore(rid)
        now = utc_now().isoformat()
        store.save_session(
            {
                "research_id": rid,
                "query": body.query,
                "status": "started",
                "current_stage": "queued",
                "progress": 0,
                "created_at": now,
                "updated_at": now,
                "errors": [],
                "message": "Research queued",
                "options": body.model_dump(),
            }
        )

        thread = threading.Thread(
            target=self._run_job,
            args=(rid, body),
            name=f"researchx-{rid}",
            daemon=True,
        )
        with self._lock:
            self._threads[rid] = thread
        thread.start()
        return {"research_id": rid, "status": "started"}

    def _build_settings(self, body: ResearchCreateRequest) -> Settings:
        # Copy current settings so per-job flags do not permanently mutate the process cache.
        settings = get_settings().model_copy(deep=True)

        mock = settings.mock_mode if body.mock_mode is None else body.mock_mode
        if mock:
            settings.mock_mode = True
            settings.llm_provider = "mock"
        if body.max_iterations is not None:
            settings.max_research_iterations = body.max_iterations
        has_docs = bool(body.pdf_paths) or bool(body.document_ids) or body.enable_pdf_rag or body.enable_document_research
        if not body.enable_web_search and not mock and not has_docs:
            # Without web search or documents outside mock mode, fall back to mock
            settings.mock_mode = True
            settings.llm_provider = "mock"
            logger.info("enable_web_search=false with no documents → forcing mock providers")
        return settings

    def _run_job(self, rid: str, body: ResearchCreateRequest) -> None:
        store = LocalStore(rid)
        try:
            store.update_session(
                status="running",
                current_stage="planning",
                progress=STAGE_PROGRESS["planning"],
                message="Starting research pipeline",
            )

            settings = self._build_settings(body)
            use_docs = body.enable_pdf_rag or body.enable_document_research or bool(body.pdf_paths) or bool(body.document_ids)
            pdf_paths = list(body.pdf_paths) if use_docs else []
            document_ids = list(body.document_ids) if use_docs else []

            def on_progress(msg: str) -> None:
                stage, progress = _map_progress_message(msg)
                # Never rewrite completed/failed from late save messages incorrectly mid-flight
                session = store.load_session() or {}
                if session.get("status") in {"completed", "failed"}:
                    return
                store.update_session(
                    status="running",
                    current_stage=stage,
                    progress=progress,
                    message=(msg or "")[:300],
                )

            workflow = ResearchWorkflow(settings=settings, progress_callback=on_progress)
            query = ResearchQuery(
                query=body.query,
                depth=ResearchDepth(body.depth),
                requirements=list(body.requirements or []),
                pdf_paths=list(pdf_paths),
                document_ids=list(document_ids),
                enable_web_search=body.enable_web_search,
                enable_document_research=use_docs,
            )
            state = workflow.run(query, research_id=rid)

            status_obj = state.get("status")
            status_val = status_obj.value if hasattr(status_obj, "value") else str(status_obj or "completed")
            plan = state.get("plan")
            subtasks = []
            if plan is not None:
                subtasks = [t.model_dump(mode="json") for t in (plan.subtasks or [])]

            report = state.get("report")
            report_dict = report.model_dump(mode="json") if report else store.read_json("report.json")
            charts: list[dict[str, Any]] = []
            if report_dict:
                charts = list(report_dict.get("charts") or []) + list(report_dict.get("chart_data") or [])

            analysis = [
                a.model_dump(mode="json") if hasattr(a, "model_dump") else a
                for a in (state.get("analysis") or [])
            ]
            if not body.enable_analysis:
                analysis = []
                charts = []

            result_payload = {
                "research_id": rid,
                "query": body.query,
                "status": status_val,
                "subtasks": subtasks,
                "sources": [
                    s.model_dump(mode="json") if hasattr(s, "model_dump") else s
                    for s in (state.get("sources") or [])
                ],
                "evidence": [
                    e.model_dump(mode="json") if hasattr(e, "model_dump") else e
                    for e in (state.get("evidence") or [])
                ],
                "claims": [
                    c.model_dump(mode="json") if hasattr(c, "model_dump") else c
                    for c in (state.get("claims") or [])
                ],
                "contradictions": [
                    c.model_dump(mode="json") if hasattr(c, "model_dump") else c
                    for c in (state.get("contradictions") or [])
                ],
                "analysis": analysis,
                "charts": charts,
                "report": report_dict,
                "errors": list(state.get("errors") or []),
                "metadata": _sanitize_meta(state.get("meta")),
            }
            store.write_json("result.json", result_payload)
            store.update_session(
                status="completed" if "fail" not in status_val else "failed",
                current_stage="completed" if "fail" not in status_val else "failed",
                progress=100,
                message="Research finished",
                pipeline_status=status_val,
                errors=list(state.get("errors") or []),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Research job %s failed: %s", rid, exc)
            store.update_session(
                status="failed",
                current_stage="failed",
                progress=100,
                message="Pipeline failure",
                errors=[str(exc)[:500]],
            )
        finally:
            with self._lock:
                self._threads.pop(rid, None)

    def _require_store(self, research_id: str) -> LocalStore:
        store = LocalStore(research_id)
        if not store.exists():
            raise ResearchNotFoundError(research_id)
        return store

    def get_status(self, research_id: str) -> dict[str, Any]:
        store = self._require_store(research_id)
        session = store.load_session() or {}
        return {
            "research_id": research_id,
            "status": session.get("status", "unknown"),
            "current_stage": session.get("current_stage"),
            "progress": int(session.get("progress") or 0),
            "message": session.get("message"),
            "errors": list(session.get("errors") or []),
        }

    def get_result(self, research_id: str) -> dict[str, Any]:
        store = self._require_store(research_id)
        session = store.load_session() or {}
        result = store.read_json("result.json")
        if isinstance(result, dict):
            result.setdefault("current_stage", session.get("current_stage"))
            result.setdefault("progress", session.get("progress", 0))
            result["metadata"] = _sanitize_meta(result.get("metadata"))
            return result

        # Fallback for in-progress or CLI-created runs
        report = store.read_json("report.json")
        sources = store.read_json("sources.json") or []
        claims = store.read_json("claims.json") or []
        evidence = store.read_json("evidence.json") or []
        contradictions = store.read_json("contradictions.json") or []
        analysis = store.read_json("analysis.json") or []
        charts: list[dict[str, Any]] = []
        if isinstance(report, dict):
            charts = list(report.get("charts") or []) + list(report.get("chart_data") or [])

        return {
            "research_id": research_id,
            "query": session.get("query") or (report or {}).get("query") or "",
            "status": session.get("status") or ("completed" if report else "running"),
            "current_stage": session.get("current_stage"),
            "progress": int(session.get("progress") or (100 if report else 0)),
            "subtasks": session.get("subtasks") or [],
            "sources": sources if isinstance(sources, list) else [],
            "evidence": evidence if isinstance(evidence, list) else [],
            "claims": claims if isinstance(claims, list) else [],
            "contradictions": contradictions if isinstance(contradictions, list) else [],
            "analysis": analysis if isinstance(analysis, list) else [],
            "charts": charts,
            "report": report if isinstance(report, dict) else None,
            "errors": list(session.get("errors") or []),
            "metadata": {},
        }

    def list_research(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> dict[str, Any]:
        items, total = LocalStore.list_sessions(limit=limit, offset=offset, status=status)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_sources(self, research_id: str) -> list[dict[str, Any]]:
        store = self._require_store(research_id)
        rows = store.read_json("sources.json") or []
        if not isinstance(rows, list):
            return []
        return [_public_source(r) for r in rows if isinstance(r, dict)]

    def get_claims(self, research_id: str) -> list[dict[str, Any]]:
        store = self._require_store(research_id)
        claims = store.read_json("claims.json") or []
        contradictions = store.read_json("contradictions.json") or []
        contradicted_ids: set[str] = set()
        if isinstance(contradictions, list):
            for c in contradictions:
                if isinstance(c, dict):
                    for cid in c.get("claim_ids") or []:
                        contradicted_ids.add(str(cid))

        out: list[dict[str, Any]] = []
        if not isinstance(claims, list):
            return out
        for c in claims:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("claim_id", ""))
            out.append(
                {
                    "claim_id": cid,
                    "claim": c.get("claim", ""),
                    "verification_status": c.get("verification_status"),
                    "confidence": c.get("confidence"),
                    "evidence_ids": list(c.get("evidence_ids") or []),
                    "source_ids": list(c.get("source_ids") or []),
                    "contradiction_status": "conflicting" if cid in contradicted_ids else "none",
                    "notes": c.get("notes") or c.get("verification_reason") or "",
                }
            )
        return out

    def get_report(self, research_id: str) -> dict[str, Any]:
        store = self._require_store(research_id)
        report = store.read_json("report.json")
        session = store.load_session() or {}
        if not isinstance(report, dict):
            status = session.get("status")
            if status == "failed":
                raise PipelineFailureError("Research failed before a report was produced")
            if status in {"running", "started"}:
                raise APIError(
                    "REPORT_NOT_READY",
                    "Report is not ready yet",
                    status_code=409,
                    details={"research_id": research_id, "status": status},
                )
            raise ResearchNotFoundError(research_id)

        analysis = store.read_json("analysis.json") or []
        charts = list(report.get("charts") or []) + list(report.get("chart_data") or [])
        sections = []
        if report.get("detailed_analysis"):
            sections.append({"title": "Detailed Analysis", "content": report["detailed_analysis"]})
        if report.get("contradictions_summary"):
            sections.append(
                {"title": "Contradictions", "content": report["contradictions_summary"]}
            )
        if report.get("conclusion"):
            sections.append({"title": "Conclusion", "content": report["conclusion"]})

        return {
            "research_id": research_id,
            "title": report.get("title", ""),
            "query": report.get("query", ""),
            "executive_summary": report.get("executive_summary", ""),
            "methodology": report.get("methodology", ""),
            "key_findings": list(report.get("key_findings") or []),
            "detailed_analysis": report.get("detailed_analysis", ""),
            "sections": sections,
            "citations": list(report.get("references") or []),
            "analysis": analysis if isinstance(analysis, list) else [],
            "charts": charts,
            "limitations": list(report.get("limitations") or []),
            "conclusion": report.get("conclusion", ""),
            "markdown": report.get("markdown", "") or store.read_text("report.md") or "",
            "status_note": report.get("status_note", ""),
        }
