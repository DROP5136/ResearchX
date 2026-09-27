"""Deterministic mock search provider."""

from __future__ import annotations

from providers.search.base import SearchProvider
from schemas.source import SearchResult


MOCK_RESULTS = [
    SearchResult(
        title="India EV Sales Cross 1.5 Million in FY2024 — Industry Brief",
        url="https://example.com/india-ev-sales-fy2024",
        snippet=(
            "Indian EV sales reached approximately 1.5 million units in FY2024. "
            "Tata Motors held about 35% of the passenger EV market share in India in 2024."
        ),
        rank=1,
    ),
    SearchResult(
        title="Indian Electric Vehicle Market Size Report 2022-2026",
        url="https://example.com/india-ev-market-size",
        snippet=(
            "India EV market size was estimated at USD 3.2 billion in 2022 and "
            "USD 5.1 billion in 2024. Analysts project continued growth through 2026."
        ),
        rank=2,
    ),
    SearchResult(
        title="OEM Market Share Snapshot — Passenger EVs India 2024",
        url="https://example.com/tata-ev-share-2024",
        snippet=(
            "Tata Motors passenger EV market share was reported at 29% for calendar year 2024. "
            "Mahindra and other OEMs continued to expand their EV portfolios."
        ),
        rank=3,
    ),
    SearchResult(
        title="FAME and EV Policy Impact in India",
        url="https://example.com/fame-ev-policy-india",
        snippet=(
            "Government incentives under FAME and state EV policies supported adoption "
            "of electric two-wheelers and four-wheelers between 2022 and 2025."
        ),
        rank=4,
    ),
]


class MockSearchProvider(SearchProvider):
    name = "mock"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        # Filter lightly by keyword overlap for realism
        q = query.lower()
        scored = []
        for r in MOCK_RESULTS:
            text = f"{r.title} {r.snippet}".lower()
            score = sum(1 for tok in q.split() if tok in text)
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        picks = [r for _, r in scored[:max_results]] or MOCK_RESULTS[:max_results]
        return [
            SearchResult(title=r.title, url=r.url, snippet=r.snippet, rank=i + 1)
            for i, r in enumerate(picks)
        ]
