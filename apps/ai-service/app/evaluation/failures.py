"""Failure classification for low-quality or failed benchmark runs."""

from __future__ import annotations

from app.evaluation.schemas import FailureCase, FailureType


def classify_failures(
    *,
    question_id: str,
    question: str,
    metrics: dict,
    expect_contradiction: bool = False,
    expect_insufficient: bool = False,
) -> list[FailureCase]:
    failures: list[FailureCase] = []

    if not metrics.get("completed", False) and metrics.get("error"):
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.REPORT,
                expected_behavior="Pipeline completes successfully",
                actual_behavior=str(metrics.get("error")),
                likely_cause="Unhandled exception during research run",
            )
        )
        return failures

    if metrics.get("source_count", 0) < 1:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.RETRIEVAL,
                expected_behavior="At least one useful source retrieved",
                actual_behavior="0 sources",
                likely_cause="Search provider empty/failed or overly strict filters",
            )
        )

    if metrics.get("claim_count", 0) == 0 and not expect_insufficient:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.EXTRACTION,
                expected_behavior="Extract at least one grounded claim",
                actual_behavior="0 claims",
                likely_cause="Extraction rejected all candidates or sources lacked content",
            )
        )

    if metrics.get("claim_support_rate", 1.0) < 0.4 and not expect_insufficient:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.FACT_CHECKING,
                expected_behavior="Majority of claims supported",
                actual_behavior=f"claim_support_rate={metrics.get('claim_support_rate')}",
                likely_cause="Weak evidence grounding or over-aggressive unsupported labeling",
            )
        )

    if metrics.get("hallucination_rate", 0.0) > 0.35:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.HALLUCINATION,
                expected_behavior="Low unsupported factual claim rate",
                actual_behavior=f"hallucination_rate={metrics.get('hallucination_rate')}",
                likely_cause="Claims without evidence / invented numbers",
            )
        )

    if metrics.get("citation_correctness", 1.0) < 0.9:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.CITATION,
                expected_behavior="All citations map to retrieved sources",
                actual_behavior=f"citation_correctness={metrics.get('citation_correctness')}",
                likely_cause="Writer invented citation IDs or references drifted",
            )
        )

    if expect_contradiction and metrics.get("contradiction_count", 0) == 0:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.CONTRADICTION,
                expected_behavior="Detect at least one contradiction",
                actual_behavior="0 contradictions",
                likely_cause="Rule/LLM contradiction detector missed aligned conflicting values",
            )
        )

    if expect_insufficient and metrics.get("insufficient_expected_met", 1.0) < 1.0:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.INSUFFICIENT_EVIDENCE,
                expected_behavior="Acknowledge insufficient/unavailable evidence",
                actual_behavior="System presented findings as established without enough support",
                likely_cause="Writer overconfident or sufficiency check too lenient",
            )
        )

    if metrics.get("numerical_applicable") and metrics.get("numerical_accuracy", 1.0) < 0.99:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.NUMERICAL,
                expected_behavior="Match expected deterministic numerical results",
                actual_behavior=str(metrics.get("numerical_details")),
                likely_cause="Analysis pipeline skipped or miscomputed YoY/CAGR",
            )
        )

    if metrics.get("topic_coverage", 1.0) < 0.34 and not expect_insufficient:
        failures.append(
            FailureCase(
                question_id=question_id,
                question=question,
                failure_type=FailureType.REPORT,
                expected_behavior="Cover expected subtopics in report/claims",
                actual_behavior=f"topic_coverage={metrics.get('topic_coverage')}",
                likely_cause="Incomplete research or report omitted key themes",
            )
        )

    return failures
