"""Search provider factory with fallback support."""

from __future__ import annotations

from config import Settings, get_settings
from providers.search.base import SearchProvider
from providers.search.duckduckgo import DuckDuckGoProvider
from providers.search.mock import MockSearchProvider
from providers.search.serper import SerperProvider
from providers.search.tavily import TavilyProvider
from schemas.source import SearchResult
from utils.logging import get_logger

logger = get_logger("researchx.search")


def _build_provider(name: str, settings: Settings) -> SearchProvider:
    name = name.lower()
    if name == "duckduckgo":
        return DuckDuckGoProvider()
    if name == "tavily":
        return TavilyProvider(api_key=settings.tavily_api_key, timeout=settings.request_timeout)
    if name == "serper":
        return SerperProvider(api_key=settings.serper_api_key, timeout=settings.request_timeout)
    if name == "mock":
        return MockSearchProvider()
    raise ValueError(f"Unsupported SEARCH_PROVIDER: {name}")


class FallbackSearchProvider(SearchProvider):
    """Try primary provider, then fallback on failure."""

    name = "fallback"

    def __init__(self, primary: SearchProvider, fallback: SearchProvider | None = None):
        self.primary = primary
        self.fallback = fallback

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            results = self.primary.search(query, max_results=max_results)
            if results:
                return results
            logger.warning("Primary search returned empty; trying fallback")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Primary search failed (%s): %s", self.primary.name, exc)

        if self.fallback is None:
            return []
        try:
            return self.fallback.search(query, max_results=max_results)
        except Exception as exc:  # noqa: BLE001
            logger.error("Fallback search failed (%s): %s", self.fallback.name, exc)
            return []


def get_search_provider(settings: Settings | None = None) -> SearchProvider:
    """Instantiate search provider with optional fallback."""
    settings = settings or get_settings()
    if settings.mock_mode:
        return MockSearchProvider()

    primary = _build_provider(settings.search_provider, settings)
    fallback_name = settings.search_fallback
    if fallback_name and fallback_name != settings.search_provider:
        try:
            fallback = _build_provider(fallback_name, settings)
        except Exception:  # noqa: BLE001
            fallback = DuckDuckGoProvider()
        return FallbackSearchProvider(primary, fallback)
    return FallbackSearchProvider(primary, DuckDuckGoProvider() if settings.search_provider != "duckduckgo" else None)


__all__ = [
    "DuckDuckGoProvider",
    "FallbackSearchProvider",
    "MockSearchProvider",
    "SearchProvider",
    "SerperProvider",
    "TavilyProvider",
    "get_search_provider",
]
