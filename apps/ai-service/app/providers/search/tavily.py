"""Tavily search provider (free tier with API key)."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.providers.search.base import SearchProvider
from app.schemas.source import SearchResult
from app.utils.logging import get_logger

logger = get_logger("researchx.search.tavily")

TAVILY_URL = "https://api.tavily.com/search"


class TavilyProvider(SearchProvider):
    name = "tavily"

    def __init__(self, api_key: str, timeout: int = 30):
        if not api_key:
            raise ValueError("TAVILY_API_KEY is required for TavilyProvider")
        self.api_key = api_key
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6), reraise=True)
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for i, item in enumerate(data.get("results", [])):
            url = item.get("url", "")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title", "") or "",
                    url=url,
                    snippet=item.get("content", "") or "",
                    rank=i + 1,
                )
            )
        return results
