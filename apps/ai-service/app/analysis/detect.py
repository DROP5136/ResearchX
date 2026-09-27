"""Detect whether a research question requires quantitative analysis."""

from __future__ import annotations

import re

QUANT_KEYWORDS = (
    "growth",
    "cagr",
    "yoy",
    "year-over-year",
    "market share",
    "market size",
    "sales",
    "revenue",
    "compare",
    "comparison",
    "percentage",
    "percent",
    "rank",
    "ranking",
    "trend",
    "average",
    "total",
    "units",
    "billion",
    "million",
    "usd",
    "₹",
    "rs.",
    "statistics",
    "metric",
    "quantitative",
    "from 20",
    "between 20",
    "2022",
    "2023",
    "2024",
    "2025",
    "2026",
)


def requires_quantitative_analysis(question: str, claim_count_numeric: int = 0) -> bool:
    """
    Heuristic: question mentions numerical analysis intent, or we already have numeric claims.
    Non-numerical questions skip the heavy analysis path.
    """
    q = (question or "").lower()
    # Explicitly non-quantitative intents
    non_quant = (
        "definition",
        "what is the meaning",
        "what is an ",
        "what is a ",
        "explain the concept",
        "define ",
    )
    if any(n in q for n in non_quant) and not any(
        k in q for k in ("growth", "cagr", "market share", "revenue", "sales", "compare")
    ):
        return False

    if any(k in q for k in QUANT_KEYWORDS):
        return True
    if re.search(r"\b20\d{2}\b", q) and any(
        w in q for w in ("analyze", "compare", "growth", "market", "sales", "share")
    ):
        return True
    # Only use numeric claim presence when the question is otherwise ambiguous
    if claim_count_numeric >= 2 and any(
        w in q for w in ("analyze", "compare", "trend", "growth", "market", "performance")
    ):
        return True
    return False
