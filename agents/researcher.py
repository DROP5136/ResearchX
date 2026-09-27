"""Research Agent — search, fetch, and collect sources for one task."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Settings, get_settings
from evidence.source import enrich_source
from prompts import load_prompt
from providers.llm.base import LLMProvider
from schemas.research import ResearchTask, TaskStatus
from schemas.source import Source
from tools.text_extractor import TextExtractor
from tools.web_search import WebSearchTool
from tools.webpage_loader import WebpageLoader
from utils.helpers import domain_from_url, new_id, safe_json_loads, utc_now
from utils.logging import get_logger, log_event

logger = get_logger("researchx.agents.researcher")

# Skip clearly irrelevant / unsafe domains from noisy free search results.
BLOCKED_DOMAINS = {
    "xvideos.com",
    "pornhub.com",
    "xhamster.com",
    "xnxx.com",
    "zhihu.com",
    "dictionary.cambridge.org",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
}


def _is_allowed_url(url: str) -> bool:
    domain = domain_from_url(url)
    if not domain:
        return False
    return not any(domain == b or domain.endswith("." + b) for b in BLOCKED_DOMAINS)


class ResearchAgent:
    """Execute a single ResearchTask end-to-end for source collection."""

    def __init__(
        self,
        llm: LLMProvider,
        search: WebSearchTool | None = None,
        settings: Settings | None = None,
    ):
        self.llm = llm
        self.settings = settings or get_settings()
        self.search = search or WebSearchTool(settings=self.settings)
        self.loader = WebpageLoader()
        self.extractor = TextExtractor()
        self.query_prompt = load_prompt("researcher")

    def research(self, task: ResearchTask, research_question: str, research_id: str = "") -> list[Source]:
        with log_event("researcher", f"research_{task.task_id}", research_id=research_id):
            task.status = TaskStatus.IN_PROGRESS
            queries = self._generate_queries(task)
            task.search_queries = queries

            hits = []
            for q in queries:
                try:
                    hits.extend(self.search.search(q, max_results=4))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Search failed for '%s': %s", q, exc)
            hits = [h for h in self.search.dedupe(hits) if _is_allowed_url(h.url)]

            # Rank by simple snippet relevance then fetch top N
            per_task_limit = max(3, self.settings.max_sources // max(1, 3))
            candidates = hits[:per_task_limit]
            sources = self._fetch_sources(candidates, task, research_question)
            sources.sort(key=lambda s: s.quality_score, reverse=True)
            task.status = TaskStatus.COMPLETED
            return sources

    def _generate_queries(self, task: ResearchTask) -> list[str]:
        user = (
            "TASK\nGenerate search queries for this research subtask.\n\n"
            f"UNTRUSTED TASK JSON\n{task.model_dump_json(indent=2)}\n\n"
            "REQUIRED OUTPUT\nJSON with search_queries array."
        )
        try:
            raw = self.llm.complete(user, system=self.query_prompt, json_mode=True, temperature=0.2)
            data = safe_json_loads(raw)
            queries = [str(q).strip() for q in data.get("search_queries", []) if str(q).strip()]
            if queries:
                return list(dict.fromkeys(queries))[:6]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Query generation failed, using heuristics: %s", exc)
        return self._heuristic_queries(task)

    @staticmethod
    def _heuristic_queries(task: ResearchTask) -> list[str]:
        base = task.question
        queries = [base]
        if task.date_range:
            queries.append(f"{base} {task.date_range}")
        for entity in task.entities[:2]:
            for metric in task.metrics[:2]:
                queries.append(f"{entity} {metric} {task.date_range or ''}".strip())
        return list(dict.fromkeys(queries))[:5]

    def _fetch_sources(self, candidates, task: ResearchTask, research_question: str) -> list[Source]:
        sources: list[Source] = []

        def _one(hit):
            html = self.loader.fetch_safe(hit.url)
            content = self.extractor.extract(html, max_length=self.settings.max_content_length)
            if not content and hit.snippet:
                content = hit.snippet
            if not content:
                return None
            passages = self.extractor.relevant_passages(content, task.question or research_question)
            focused = "\n\n".join(passages) if passages else content[:3000]
            source = Source(
                source_id=new_id("SRC"),
                url=hit.url,
                title=hit.title or domain_from_url(hit.url),
                domain=domain_from_url(hit.url),
                retrieved_at=utc_now(),
                content=focused,
                snippet=hit.snippet,
                task_ids=[task.task_id],
            )
            return enrich_source(source, research_question)

        max_workers = min(self.settings.max_concurrent_agents, max(1, len(candidates)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_one, hit): hit for hit in candidates}
            for fut in as_completed(futures):
                try:
                    src = fut.result()
                    if src:
                        sources.append(src)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Source fetch worker failed: %s", exc)
        return sources
