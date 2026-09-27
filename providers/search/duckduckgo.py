"""DuckDuckGo search provider (no API key required)."""

from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from providers.search.base import SearchProvider
from schemas.source import SearchResult
from utils.logging import get_logger

logger = get_logger("researchx.search.duckduckgo")


class DuckDuckGoProvider(SearchProvider):
    """Uses the duckduckgo-search package (free, no key)."""

    name = "duckduckgo"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6), reraise=True)
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            from duckduckgo_search import DDGS
        except ImportError as exc:
            raise RuntimeError("duckduckgo-search is not installed") from exc

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
        for i, item in enumerate(raw):
            url = item.get("href") or item.get("link") or ""
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title", "") or "",
                    url=url,
                    snippet=item.get("body", "") or item.get("snippet", "") or "",
                    rank=i + 1,
                )
            )
        logger.debug("DDG search '%s' -> %d hits", query, len(results))
        return results
