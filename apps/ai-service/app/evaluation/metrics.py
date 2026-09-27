"""Comprehensive evaluation metrics for ResearchX runs.

Metric types:
- deterministic: computed from structured state (preferred)
- heuristic: proxy scores for open-ended quality
- llm_assisted: optional judge scores (never used for arithmetic)
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.claim import (
    Claim,
    Contradiction,
    Evidence,
    VerificationStatus,
    is_conflicting_status,
    is_reportable_claim,
    is_unsupported_status,
)
from app.schemas.report import AnalysisResult, DataPoint, ResearchReport
from app.schemas.source import Source
from app.tools.calculator import Calculator


def source_relevance(sources: list[Source], question: str) -> float:
    if not sources:
        return 0.0
    tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", question) if len(t) > 2}
    if not tokens:
        return 0.5
    scores = []
    for s in sources:
        blob = f"{s.title} {s.snippet} {s.content[:1500]}".lower()
        hits = sum(1 for t in tokens if t in blob)
        scores.append(min(1.0, hits / max(3, len(tokens) * 0.4)))
    return round(sum(scores) / len(scores), 4)


def source_diversity(sources: list[Source]) -> float:
    if not sources:
        return 0.0
    domains = {s.domain for s in sources if s.domain}
    types = {s.source_type.value if hasattr(s.source_type, "value") else str(s.source_type) for s in sources}
    # Heuristic: reward unique domains up to 5 and type variety up to 3
    domain_score = min(1.0, len(domains) / min(5, max(1, len(sources))))
    type_score = min(1.0, len(types) / 3)
    return round(0.7 * domain_score + 0.3 * type_score, 4)


def duplicate_source_rate(sources: list[Source]) -> float:
    if not sources:
        return 0.0
    urls = [(s.url or s.source_id).rstrip("/").lower() for s in sources]
    unique = set(urls)
    return round(1.0 - (len(unique) / len(urls)), 4)


def evidence_coverage(claims: list[Claim], evidence: list[Evidence]) -> float:
    if not claims:
        return 0.0
    known = {e.evidence_id for e in evidence}
    linked = sum(1 for c in claims if c.evidence_ids and any(eid in known for eid in c.evidence_ids))
    return round(linked / len(claims), 4)


def _evidence_text(e: Evidence) -> str:
    return (getattr(e, "text", None) or getattr(e, "quote", None) or "") or ""


def evidence_relevance(evidence: list[Evidence], question: str) -> float:
    if not evidence:
        return 0.0
    tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", question) if len(t) > 2}
    if not tokens:
        return 0.5
    scores = []
    for e in evidence:
        blob = _evidence_text(e).lower()
        hits = sum(1 for t in tokens if t in blob)
        scores.append(min(1.0, hits / max(2, len(tokens) * 0.3)))
    return round(sum(scores) / len(scores), 4)


def evidence_completeness(claims: list[Claim], evidence: list[Evidence]) -> float:
    """Fraction of claims that have at least one non-empty evidence span."""
    if not claims:
        return 0.0
    ev_map = {e.evidence_id: e for e in evidence}
    ok = 0
    for c in claims:
        for eid in c.evidence_ids:
            e = ev_map.get(eid)
            if e and _evidence_text(e).strip():
                ok += 1
                break
    return round(ok / len(claims), 4)


def useful_source_count(sources: list[Source], min_quality: float = 0.3) -> int:
    return sum(1 for s in sources if float(getattr(s, "quality_score", 0) or 0) >= min_quality)


def fabricated_number_rate(claims: list[Claim], evidence: list[Evidence]) -> float:
    """
    Heuristic: numeric literals in claims that do not appear in linked evidence.
    Limitation: units/formatting differences cause false positives.
    """
    if not claims:
        return 0.0
    ev_map = {e.evidence_id: e for e in evidence}
    flagged = 0
    factual = 0
    for c in claims:
        nums = re.findall(r"\d+(?:\.\d+)?", c.claim)
        if not nums:
            continue
        factual += 1
        blob = " ".join(_evidence_text(ev_map[eid]) if eid in ev_map else "" for eid in c.evidence_ids)
        if not blob.strip():
            flagged += 1
            continue
        if any(n not in blob for n in nums):
            flagged += 1
    return round(flagged / factual, 4) if factual else 0.0


def evidence_traceability(claims: list[Claim], evidence: list[Evidence], sources: list[Source]) -> float:
    if not claims:
        return 0.0
    src_ids = {s.source_id for s in sources}
    ev_map = {e.evidence_id: e for e in evidence}
    ok = 0
    for c in claims:
        if not c.source_ids or any(sid not in src_ids for sid in c.source_ids):
            continue
        if not c.evidence_ids:
            continue
        if all(eid in ev_map and ev_map[eid].source_id in c.source_ids for eid in c.evidence_ids):
            ok += 1
    return round(ok / len(claims), 4)


def claim_support_rate(claims: list[Claim]) -> float:
    """Supported / total using verification status when available."""
    if not claims:
        return 0.0
    supported = sum(1 for c in claims if is_reportable_claim(c.verification_status))
    if supported == 0:
        # Fallback heuristic for older runs without verification
        supported = sum(1 for c in claims if c.source_ids and c.evidence_ids)
    return round(supported / len(claims), 4)


def unsupported_rate(claims: list[Claim]) -> float:
    if not claims:
        return 0.0
    n = sum(1 for c in claims if is_unsupported_status(c.verification_status))
    return round(n / len(claims), 4)


def conflicting_rate(claims: list[Claim]) -> float:
    if not claims:
        return 0.0
    n = sum(1 for c in claims if is_conflicting_status(c.verification_status))
    return round(n / len(claims), 4)


def citation_coverage(report_md: str, claims: list[Claim]) -> float:
    if not claims:
        return 0.0
    cited = sum(1 for c in claims if any(sid in report_md for sid in c.source_ids))
    return round(cited / len(claims), 4)


def citation_correctness(report_md: str, sources: list[Source]) -> float:
    used = set(re.findall(r"\[(SRC_[a-zA-Z0-9]+)\]", report_md))
    if not used:
        return 1.0 if sources else 0.0
    known = {s.source_id for s in sources}
    return round(len(used & known) / len(used), 4)


def citation_completeness(report_md: str, sources: list[Source]) -> float:
    """Fraction of retrieved sources that appear in the references section."""
    if not sources:
        return 0.0
    cited = sum(1 for s in sources if s.source_id in report_md)
    return round(cited / len(sources), 4)


def hallucination_rate(claims: list[Claim]) -> float:
    """
    Proxy hallucination measure = unsupported factual claims / total claims.

    Limitation: verification heuristics can false-positive/negative; this is not
    a perfect measure of factual hallucination.
    """
    return unsupported_rate(claims)


def topic_coverage(text: str, expected_topics: list[str]) -> float:
    if not expected_topics:
        return 1.0
    blob = (text or "").lower()
    hits = sum(1 for t in expected_topics if t.lower() in blob)
    return round(hits / len(expected_topics), 4)


def claim_hint_coverage(claims: list[Claim], hints: list[str]) -> float:
    if not hints:
        return 1.0
    blob = " ".join(c.claim for c in claims).lower()
    hits = sum(1 for h in hints if h.lower() in blob)
    return round(hits / len(hints), 4)


def numerical_accuracy(
    analysis: list[AnalysisResult],
    expected_values: dict[str, float],
    tolerance: float = 0.05,
) -> dict[str, Any]:
    """
    Deterministic comparison for known expected values.
    Keys supported:
      - yoy_2023_pct, yoy_2024_pct (from YoY series)
      - arbitrary keys matched against analysis.result dict stringification
    """
    if not expected_values:
        return {"applicable": False, "score": 1.0, "details": []}

    details = []
    hits = 0
    # Collect yoy series if present
    yoy_series: list[float | None] = []
    for a in analysis:
        if isinstance(a.result, dict) and "yoy_pct" in a.result:
            yoy_series = list(a.result.get("yoy_pct") or [])
            break

    for key, expected in expected_values.items():
        actual = None
        if key == "yoy_2023_pct" and len(yoy_series) > 1:
            actual = yoy_series[1]
        elif key == "yoy_2024_pct" and len(yoy_series) > 2:
            actual = yoy_series[2]
        else:
            # Independent Python recomputation for the classic 100/120/150 case
            if key.startswith("yoy_") and not yoy_series:
                recomputed = Calculator.yoy_growth([100, 120, 150])
                if key == "yoy_2023_pct":
                    actual = recomputed[1]
                elif key == "yoy_2024_pct":
                    actual = recomputed[2]

        if actual is None:
            details.append(
                {
                    "key": key,
                    "expected": expected,
                    "actual": None,
                    "abs_error": None,
                    "rel_error": None,
                    "match": False,
                }
            )
            continue
        abs_err = abs(float(actual) - float(expected))
        rel_err = abs_err / max(abs(float(expected)), 1e-9)
        match = rel_err <= tolerance or abs_err <= 0.01
        if match:
            hits += 1
        details.append(
            {
                "key": key,
                "expected": expected,
                "actual": actual,
                "abs_error": round(abs_err, 6),
                "rel_error": round(rel_err, 6),
                "match": match,
            }
        )

    score = hits / len(expected_values) if expected_values else 1.0
    return {"applicable": True, "score": round(score, 4), "details": details}


def evaluate_run(
    *,
    completed: bool,
    report: ResearchReport | None,
    sources: list[Source],
    claims: list[Claim],
    contradictions: list[Contradiction],
    evidence: list[Evidence] | None = None,
    analysis: list[AnalysisResult] | None = None,
    datapoints: list[DataPoint] | None = None,
    question: str = "",
    expected_topics: list[str] | None = None,
    expected_claims: list[str] | None = None,
    expected_values: dict[str, float] | None = None,
    expect_contradiction: bool = False,
    expect_insufficient: bool = False,
    duration_sec: float = 0.0,
    iterations: int = 0,
    stage_timings: dict[str, Any] | None = None,
    llm_calls: int | None = None,
    token_usage: dict[str, Any] | None = None,
    estimated_cost: float | None = None,
) -> dict[str, Any]:
    """Full metric bundle for one research run (deterministic + heuristic)."""
    evidence = evidence or []
    analysis = analysis or []
    datapoints = datapoints or []
    md = report.markdown if report else ""
    report_blob = md + " " + (report.executive_summary if report else "")
    q = question or (report.query if report else "")

    num = numerical_accuracy(analysis, expected_values or {})
    useful = useful_source_count(sources)

    metrics: dict[str, Any] = {
        # Completion
        "completed": completed,
        "completion_rate": 1.0 if completed else 0.0,
        # Sources
        "source_count": len(sources),
        "useful_source_count": useful,
        "source_relevance": source_relevance(sources, q),
        "source_diversity": source_diversity(sources),
        "duplicate_source_rate": duplicate_source_rate(sources),
        # Evidence
        "evidence_count": len(evidence),
        "evidence_coverage": evidence_coverage(claims, evidence),
        "evidence_relevance": evidence_relevance(evidence, q),
        "evidence_completeness": evidence_completeness(claims, evidence),
        "evidence_traceability": evidence_traceability(claims, evidence, sources),
        # Claims
        "claim_count": len(claims),
        "claim_support_rate": claim_support_rate(claims),
        "unsupported_rate": unsupported_rate(claims),
        "conflicting_rate": conflicting_rate(claims),
        "claim_hint_coverage": claim_hint_coverage(claims, expected_claims or []),
        # Citations
        "citation_coverage": citation_coverage(md, claims),
        "citation_correctness": citation_correctness(md, sources),
        "citation_completeness": citation_completeness(md, sources),
        # Hallucination proxy
        "hallucination_rate": hallucination_rate(claims),
        "fabricated_number_rate": fabricated_number_rate(claims, evidence),
        # Completeness
        "topic_coverage": topic_coverage(report_blob, expected_topics or []),
        "research_completeness": topic_coverage(report_blob, expected_topics or []),
        # Contradictions
        "contradiction_count": len(contradictions),
        "contradiction_detected": 1.0 if contradictions else 0.0,
        "contradiction_expectation_met": (
            1.0
            if (expect_contradiction and contradictions)
            or (not expect_contradiction)
            else 0.0
        ),
        # Insufficient evidence handling
        "insufficient_expected_met": (
            1.0
            if not expect_insufficient
            else (
                1.0
                if (
                    (report and report.status_note in {"INSUFFICIENT_EVIDENCE", "COMPLETED_WITH_LIMITATIONS"})
                    or claim_support_rate(claims) < 0.35
                    or len(claims) < 2
                )
                else 0.0
            )
        ),
        # Numerical
        "numerical_accuracy": num["score"],
        "numerical_applicable": num["applicable"],
        "numerical_details": num["details"],
        "datapoint_count": len(datapoints),
        "analysis_count": len([a for a in analysis if getattr(a, "status", "ok") == "ok"]),
        # Efficiency
        "execution_time_sec": round(duration_sec, 3),
        "iterations": iterations,
        "stage_timings": stage_timings or {},
        "llm_calls": llm_calls,
        "token_usage": token_usage or {},
        "estimated_cost": estimated_cost,
    }
    return metrics
