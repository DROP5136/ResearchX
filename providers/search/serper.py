"""Serper.dev Google search provider (free tier with API key)."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from providers.search.base import SearchProvider
from schemas.source import SearchResult
from utils.logging import get_logger

logger = get_logger("researchx.search.serper")

SERPER_URL = "https://google.serper.dev/search"


class SerperProvider(SearchProvider):
    name = "serper"

    def __init__(self, api_key: str, timeout: int = 30):
        if not api_key:
            raise ValueError("SERPER_API_KEY is required for SerperProvider")
        self.api_key = api_key
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6), reraise=True)
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": max_results}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(SERPER_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for i, item in enumerate(data.get("organic", [])[:max_results]):
            url = item.get("link", "")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title", "") or "",
                    url=url,
                    snippet=item.get("snippet", "") or "",
                    rank=i + 1,
                )
            )
        return results
