"""Markdown + dashboard JSON report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.regression import compare_aggregates, format_regression_table
from evaluation.schemas import EvalAggregate


def to_dashboard_json(agg: EvalAggregate) -> dict[str, Any]:
    return {
        "overall": agg.overall,
        "performance": agg.performance,
        "by_category": agg.by_category,
        "failures": [f.model_dump() for f in agg.failures],
        "n": agg.n,
        "mode": agg.mode,
        "generated_at": agg.generated_at,
        "results": [
            {
                "id": r.id,
                "question": r.question,
                "category": r.category,
                "completed": r.completed,
                "metrics": r.metrics,
                "failures": [f.model_dump() for f in r.failures],
                "judge": r.judge.model_dump() if r.judge else None,
                "error": r.error,
            }
            for r in agg.results
        ],
    }


def write_markdown_report(
    agg: EvalAggregate,
    path: Path,
    *,
    baseline: dict[str, Any] | None = None,
) -> Path:
    lines = [
        "# ResearchX Evaluation Report",
        "",
        f"**Mode:** `{agg.mode}`  ",
        f"**Questions:** {agg.n}  ",
        f"**Generated:** {agg.generated_at}",
        "",
        "## Overall Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for k, v in sorted(agg.overall.items()):
        if isinstance(v, float):
            lines.append(f"| {k} | {v:.4f} |")
        else:
            lines.append(f"| {k} | {v} |")

    lines += [
        "",
        "## Source Retrieval",
        "",
        f"- Avg sources: **{agg.performance.get('avg_sources', 0):.2f}**",
        f"- Source relevance: **{agg.overall.get('source_relevance', 0):.4f}**",
        f"- Source diversity: **{agg.overall.get('source_diversity', 0):.4f}**",
        f"- Duplicate source rate: **{agg.overall.get('duplicate_source_rate', 0):.4f}**",
        "",
        "## Evidence Extraction",
        "",
        f"- Evidence coverage: **{agg.overall.get('evidence_coverage', 0):.4f}**",
        f"- Evidence traceability: **{agg.overall.get('evidence_traceability', 0):.4f}**",
        "",
        "## Claim Verification",
        "",
        f"- Claim support rate: **{agg.overall.get('claim_support_rate', 0):.4f}**",
        f"- Unsupported rate: **{agg.overall.get('unsupported_rate', 0):.4f}**",
        f"- Conflicting rate: **{agg.overall.get('conflicting_rate', 0):.4f}**",
        "",
        "## Citation Accuracy",
        "",
        f"- Citation coverage: **{agg.overall.get('citation_coverage', 0):.4f}**",
        f"- Citation correctness: **{agg.overall.get('citation_correctness', 0):.4f}**",
        f"- Citation completeness: **{agg.overall.get('citation_completeness', 0):.4f}**",
        "",
        "## Hallucination",
        "",
        f"- Hallucination rate (proxy): **{agg.overall.get('hallucination_rate', 0):.4f}**",
        "",
        "> **Limitation:** This is a proxy = unsupported claims / total claims. "
        "It can false-positive when verification is conservative, and false-negative "
        "when unsupported claims are mislabeled as supported.",
        "",
        "## Numerical Accuracy",
        "",
        f"- Numerical accuracy: **{agg.overall.get('numerical_accuracy', 0):.4f}**",
        "",
        "## Research Completeness",
        "",
        f"- Topic coverage: **{agg.overall.get('topic_coverage', 0):.4f}**",
        f"- Claim hint coverage: **{agg.overall.get('claim_hint_coverage', 0):.4f}**",
        "",
        "## Performance",
        "",
        f"- Avg execution time (s): **{agg.performance.get('avg_execution_time', 0):.3f}**",
        f"- Avg iterations: **{agg.performance.get('avg_iterations', 0):.2f}**",
        f"- Avg sources: **{agg.performance.get('avg_sources', 0):.2f}**",
        f"- Avg claims: **{agg.performance.get('avg_claims', 0):.2f}**",
        "",
    ]

    if baseline:
        lines += ["## Regression vs Baseline", "", format_regression_table(compare_aggregates(baseline, to_dashboard_json(agg)))]

    lines += ["## Per-Question Results", ""]
    for r in agg.results:
        status = "OK" if r.completed and not r.failures else "ISSUES"
        lines.append(f"### {r.id} — {status}")
        lines.append(f"- Question: {r.question}")
        lines.append(f"- Category: `{r.category}` / difficulty `{r.difficulty}`")
        if r.error:
            lines.append(f"- Error: `{r.error}`")
        m = r.metrics
        lines.append(
            f"- Support={m.get('claim_support_rate', 0):.2f}, "
            f"CiteCorr={m.get('citation_correctness', 0):.2f}, "
            f"Halluc={m.get('hallucination_rate', 0):.2f}, "
            f"Topics={m.get('topic_coverage', 0):.2f}, "
            f"Time={m.get('execution_time_sec', 0):.2f}s"
        )
        if r.judge:
            lines.append(
                f"- Judge: rel={r.judge.relevance:.2f} comp={r.judge.completeness:.2f} "
                f"ground={r.judge.groundedness:.2f} clarity={r.judge.clarity:.2f}"
            )
        lines.append("")

    lines += ["## Failure Cases", ""]
    if not agg.failures:
        lines.append("_No classified failures._")
    else:
        for f in agg.failures:
            lines.append(f"### {f.question_id} — `{f.failure_type.value}`")
            lines.append(f"- Expected: {f.expected_behavior}")
            lines.append(f"- Actual: {f.actual_behavior}")
            lines.append(f"- Likely cause: {f.likely_cause}")
            lines.append("")

    lines += [
        "## Recommendations",
        "",
        "- Improve retrieval diversity for low `source_diversity` cases.",
        "- Tighten evidence-span grounding where hallucination proxy is high.",
        "- Expand synthetic numerical gold cases for stronger arithmetic regression coverage.",
        "- Keep LLM-as-judge optional; rely on deterministic metrics for CI gates.",
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
