"""Abstract search provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from schemas.source import SearchResult


class SearchProvider(ABC):
    """Provider-agnostic web search interface."""

    name: str = "base"

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Return ranked search results for a query."""
