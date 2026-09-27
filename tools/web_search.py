"""Web search tool wrapping the search provider + cache."""

from __future__ import annotations

from config import Settings, get_settings
from providers.search import get_search_provider
from providers.search.base import SearchProvider
from schemas.source import SearchResult
from storage.local_store import FileCache
from utils.logging import get_logger

logger = get_logger("researchx.tools.search")


class WebSearchTool:
    """Search with caching and URL deduplication."""

    def __init__(
        self,
        provider: SearchProvider | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.provider = provider or get_search_provider(self.settings)
        self.cache = FileCache("search")

    def search(self, query: str, max_results: int | None = None) -> list[SearchResult]:
        max_results = max_results or min(8, self.settings.max_sources)
        cached = self.cache.get("search", self.provider.name, query, str(max_results))
        if cached is not None:
            return [SearchResult.model_validate(x) for x in cached]

        results = self.provider.search(query, max_results=max_results)
        self.cache.set(
            "search",
            self.provider.name,
            query,
            str(max_results),
            value=[r.model_dump() for r in results],
        )
        return results

    @staticmethod
    def dedupe(results: list[SearchResult]) -> list[SearchResult]:
        seen: set[str] = set()
        unique: list[SearchResult] = []
        for r in results:
            key = r.url.rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(r)
        return unique
