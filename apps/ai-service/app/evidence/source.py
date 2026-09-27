"""Source quality heuristics (prioritization only — not truth)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.schemas.source import Source, SourceType
from app.utils.helpers import domain_from_url


GOV_SUFFIXES = (".gov", ".gov.in", ".nic.in", ".edu", ".ac.in", ".ac.uk")
NEWS_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "economist.com",
    "bbc.com",
    "bbc.co.uk",
    "thehindu.com",
    "indianexpress.com",
    "livemint.com",
    "economictimes.indiatimes.com",
    "business-standard.com",
    "financialexpress.com",
}
INDUSTRY_HINTS = ("report", "research", "analytics", "insights", "whitepaper")
FORUM_DOMAINS = {"reddit.com", "quora.com", "medium.com", "stackoverflow.com", "twitter.com", "x.com"}


def classify_source_type(url: str, title: str = "") -> SourceType:
    domain = domain_from_url(url)
    lower = f"{domain} {title}".lower()
    if any(domain.endswith(s) or s in domain for s in (".gov", "gov.in", "nic.in")):
        return SourceType.GOVERNMENT
    if any(domain.endswith(s) or ".edu" in domain or ".ac." in domain for s in GOV_SUFFIXES):
        return SourceType.ACADEMIC
    if domain in FORUM_DOMAINS or "forum" in lower or "blog" in lower:
        if domain in FORUM_DOMAINS:
            return SourceType.FORUM
        return SourceType.BLOG
    if domain in NEWS_DOMAINS or any(x in lower for x in ("news", "times", "post", "gazette")):
        return SourceType.NEWS
    if any(h in lower for h in INDUSTRY_HINTS):
        return SourceType.INDUSTRY
    if url.lower().endswith(".pdf"):
        return SourceType.PDF
    return SourceType.OTHER


def score_source(
    *,
    url: str,
    title: str,
    snippet: str,
    content: str,
    query: str,
    published_at: str | None = None,
) -> dict[str, float | bool | SourceType]:
    """Return transparent heuristic scores for prioritization."""
    source_type = classify_source_type(url, title)
    domain = domain_from_url(url)

    authority = {
        SourceType.GOVERNMENT: 0.95,
        SourceType.ACADEMIC: 0.9,
        SourceType.COMPANY: 0.75,
        SourceType.INDUSTRY: 0.8,
        SourceType.NEWS: 0.7,
        SourceType.PDF: 0.65,
        SourceType.BLOG: 0.35,
        SourceType.FORUM: 0.2,
        SourceType.OTHER: 0.4,
    }.get(source_type, 0.4)

    # Relevance via token overlap
    tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", query) if len(t) > 2}
    blob = f"{title} {snippet} {content[:2000]}".lower()
    hits = sum(1 for t in tokens if t in blob)
    relevance = min(1.0, hits / max(3, len(tokens) * 0.5)) if tokens else 0.3

    # Recency boost if year mentioned near current topic years
    recency = 0.5
    years = re.findall(r"20\d{2}", f"{published_at or ''} {blob}")
    if years:
        latest = max(int(y) for y in years)
        age = max(0, datetime.now(timezone.utc).year - latest)
        recency = max(0.2, 1.0 - age * 0.15)

    specificity = 0.4
    if re.search(r"\d[\d,]*(\.\d+)?\s*%?", content[:3000]):
        specificity = 0.75
    if re.search(r"\b(Q[1-4]|FY\d{2,4}|20\d{2})\b", content[:3000], re.I):
        specificity = min(1.0, specificity + 0.15)

    is_primary = source_type in {SourceType.GOVERNMENT, SourceType.COMPANY, SourceType.ACADEMIC}
    quality = round(
        0.35 * float(authority)
        + 0.30 * float(relevance)
        + 0.15 * float(recency)
        + 0.15 * float(specificity)
        + (0.05 if is_primary else 0.0),
        3,
    )
    return {
        "source_type": source_type,
        "authority_score": round(float(authority), 3),
        "relevance_score": round(float(relevance), 3),
        "quality_score": quality,
        "is_primary": is_primary,
        "domain": domain,
    }


def enrich_source(source: Source, query: str, *, preserve_type: bool = False) -> Source:
    scores = score_source(
        url=source.url,
        title=source.title,
        snippet=source.snippet,
        content=source.content,
        query=query,
        published_at=source.published_at,
    )
    if source.domain == "local-pdf" or source.source_type == SourceType.PDF or preserve_type:
        # Keep document sources as PDF; still refresh relevance/quality scores
        source.authority_score = max(float(scores["authority_score"]), 0.7)
        source.relevance_score = float(scores["relevance_score"])
        source.quality_score = float(scores["quality_score"])
        source.is_primary = True
        source.source_type = SourceType.PDF
        source.domain = source.domain or "local-pdf"
        return source
    source.source_type = scores["source_type"]  # type: ignore[assignment]
    source.authority_score = float(scores["authority_score"])
    source.relevance_score = float(scores["relevance_score"])
    source.quality_score = float(scores["quality_score"])
    source.is_primary = bool(scores["is_primary"])
    source.domain = str(scores["domain"]) or source.domain
    return source
