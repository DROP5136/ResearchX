"""Search provider tests."""

from __future__ import annotations

from app.providers.search.base import SearchProvider
from app.providers.search.mock import MockSearchProvider
from app.schemas.source import SearchResult
from app.tools.web_search import WebSearchTool


def test_mock_search_returns_results():
    provider = MockSearchProvider()
    results = provider.search("Indian EV market sales", max_results=3)
    assert isinstance(provider, SearchProvider)
    assert len(results) <= 3
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(r.url for r in results)


def test_search_deduplication():
    results = [
        SearchResult(title="A", url="https://example.com/a", snippet="x", rank=1),
        SearchResult(title="A2", url="https://example.com/a/", snippet="y", rank=2),
        SearchResult(title="B", url="https://example.com/b", snippet="z", rank=3),
    ]
    unique = WebSearchTool.dedupe(results)
    assert len(unique) == 2


def test_empty_query_still_returns_list():
    provider = MockSearchProvider()
    results = provider.search("", max_results=2)
    assert isinstance(results, list)
