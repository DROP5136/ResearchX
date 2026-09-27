"""Baseline vs current evaluation regression comparison."""

from __future__ import annotations

from typing import Any


PRIMARY_METRICS = [
    "claim_support_rate",
    "citation_coverage",
    "citation_correctness",
    "hallucination_rate",
    "topic_coverage",
    "numerical_accuracy",
    "source_relevance",
    "evidence_traceability",
    "completion_rate",
]


# For hallucination_rate, lower is better
LOWER_IS_BETTER = {"hallucination_rate", "duplicate_source_rate", "unsupported_rate"}


def compare_aggregates(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    base_overall = baseline.get("overall") or {}
    curr_overall = current.get("overall") or {}
    rows = []
    keys = sorted(set(PRIMARY_METRICS) | set(base_overall) | set(curr_overall))
    for key in keys:
        b = base_overall.get(key)
        c = curr_overall.get(key)
        if not isinstance(b, (int, float)) or not isinstance(c, (int, float)):
            continue
        diff = round(float(c) - float(b), 4)
        if key in LOWER_IS_BETTER:
            status = "improved" if diff < -1e-6 else ("regressed" if diff > 1e-6 else "unchanged")
        else:
            status = "improved" if diff > 1e-6 else ("regressed" if diff < -1e-6 else "unchanged")
        rows.append(
            {
                "metric": key,
                "baseline": round(float(b), 4),
                "current": round(float(c), 4),
                "difference": diff,
                "status": status,
            }
        )
    return rows


def format_regression_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No comparable metrics._\n"
    lines = [
        "| Metric | Baseline | Current | Difference | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['metric']} | {r['baseline']:.4f} | {r['current']:.4f} | "
            f"{r['difference']:+.4f} | {r['status']} |"
        )
    return "\n".join(lines) + "\n"
