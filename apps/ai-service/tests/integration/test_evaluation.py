"""Unit + integration tests for the ResearchX evaluation framework."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.evaluation.failures import classify_failures
from app.evaluation.metrics import (
    claim_support_rate,
    citation_coverage,
    citation_correctness,
    evaluate_run,
    hallucination_rate,
    numerical_accuracy,
    topic_coverage,
)
from app.evaluation.regression import compare_aggregates
from app.evaluation.run import aggregate_results, load_benchmarks, run_evaluation
from app.evaluation.schemas import BenchmarkItem, FailureType, QuestionEvalResult
from app.schemas.claim import Claim, Evidence, VerificationStatus
from app.schemas.report import AnalysisResult, AnalysisType, ResearchReport
from app.schemas.source import Source, SourceType
from app.tools.calculator import Calculator


def _src(sid: str = "SRC_a") -> Source:
    return Source(
        source_id=sid,
        title="Test source about market growth",
        url=f"https://example.com/{sid}",
        snippet="market growth sales",
        content="market growth and sales figures for testing",
        source_type=SourceType.OTHER,
        domain="example.com",
        quality_score=0.8,
    )


def _claim(
    text: str,
    *,
    status: VerificationStatus = VerificationStatus.SUPPORTED,
    sources: list[str] | None = None,
    evidence_ids: list[str] | None = None,
) -> Claim:
    return Claim(
        claim_id="CLM_1",
        claim=text,
        source_ids=sources or ["SRC_a"],
        evidence_ids=evidence_ids or ["EVD_1"],
        verification_status=status,
    )


def test_benchmark_loading():
    items = load_benchmarks()
    assert 15 <= len(items) <= 30
    assert all(isinstance(i, BenchmarkItem) for i in items)
    assert any(i.expected_values for i in items)
    assert any(i.expect_insufficient for i in items)


def test_malformed_benchmark_item():
    with pytest.raises(ValidationError):
        BenchmarkItem.model_validate({"id": "X", "question": 123})


def test_claim_support_rate():
    claims = [
        _claim("a", status=VerificationStatus.SUPPORTED),
        _claim("b", status=VerificationStatus.UNSUPPORTED),
        _claim("c", status=VerificationStatus.PARTIALLY_SUPPORTED),
    ]
    rate = claim_support_rate(claims)
    assert 0.0 < rate <= 1.0


def test_citation_coverage_and_correctness():
    sources = [_src("SRC_a"), _src("SRC_b")]
    claims = [_claim("sales grew", sources=["SRC_a"])]
    md = "Finding [SRC_a].\n\n## References\n- SRC_a\n- SRC_b\n"
    assert citation_coverage(md, claims) == 1.0
    assert citation_correctness(md, sources) == 1.0
    bad = "Finding [SRC_fake]."
    assert citation_correctness(bad, sources) == 0.0


def test_hallucination_rate_proxy():
    claims = [
        _claim("ok", status=VerificationStatus.SUPPORTED),
        _claim("bad", status=VerificationStatus.UNSUPPORTED),
    ]
    assert hallucination_rate(claims) == 0.5


def test_numerical_accuracy_deterministic():
    yoy = Calculator.yoy_growth([100, 120, 150])
    analysis = [
        AnalysisResult(
            analysis_type=AnalysisType.YOY,
            metric="yoy",
            result={"yoy_pct": yoy},
            status="ok",
        )
    ]
    out = numerical_accuracy(analysis, {"yoy_2023_pct": 20.0, "yoy_2024_pct": 25.0})
    assert out["applicable"] is True
    assert out["score"] == 1.0


def test_topic_coverage_completeness():
    text = "The report covers market size, sales growth, and policy incentives."
    assert topic_coverage(text, ["market size", "sales", "policy"]) == 1.0
    assert topic_coverage(text, ["quantum bananas"]) == 0.0


def test_evaluate_run_bundle():
    sources = [_src()]
    evidence = [
        Evidence(
            evidence_id="EVD_1",
            source_id="SRC_a",
            text="sales grew 20 percent in 2023",
        )
    ]
    claims = [_claim("sales grew 20 percent", evidence_ids=["EVD_1"])]
    report = ResearchReport(
        research_id="R1",
        title="T",
        query="sales growth",
        markdown="sales [SRC_a]\n## References\nSRC_a",
        key_findings=["sales grew"],
        status_note="COMPLETED",
    )
    m = evaluate_run(
        completed=True,
        report=report,
        sources=sources,
        claims=claims,
        contradictions=[],
        evidence=evidence,
        question="sales growth market",
        expected_topics=["sales"],
        duration_sec=1.2,
        iterations=1,
    )
    assert m["completed"] is True
    assert m["claim_support_rate"] >= 0.0
    assert m["citation_correctness"] == 1.0
    assert "hallucination_rate" in m


def test_regression_comparison():
    baseline = {"overall": {"claim_support_rate": 0.7, "hallucination_rate": 0.2}}
    current = {"overall": {"claim_support_rate": 0.8, "hallucination_rate": 0.1}}
    rows = compare_aggregates(baseline, current)
    by_metric = {r["metric"]: r for r in rows}
    assert by_metric["claim_support_rate"]["status"] == "improved"
    assert by_metric["hallucination_rate"]["status"] == "improved"


def test_failure_classification_retrieval():
    failures = classify_failures(
        question_id="B99",
        question="q",
        metrics={"completed": True, "source_count": 0, "claim_count": 0},
    )
    types = {f.failure_type for f in failures}
    assert FailureType.RETRIEVAL in types


def test_aggregation():
    results = [
        QuestionEvalResult(
            id="B01",
            question="q1",
            category="general_factual",
            completed=True,
            metrics={
                "completion_rate": 1.0,
                "claim_support_rate": 0.8,
                "citation_coverage": 0.9,
                "citation_correctness": 1.0,
                "citation_completeness": 0.5,
                "hallucination_rate": 0.1,
                "fabricated_number_rate": 0.0,
                "topic_coverage": 0.7,
                "claim_hint_coverage": 0.5,
                "source_relevance": 0.6,
                "source_diversity": 0.5,
                "duplicate_source_rate": 0.0,
                "evidence_coverage": 0.8,
                "evidence_relevance": 0.5,
                "evidence_completeness": 0.8,
                "evidence_traceability": 0.7,
                "numerical_accuracy": 1.0,
                "unsupported_rate": 0.1,
                "conflicting_rate": 0.0,
                "contradiction_expectation_met": 1.0,
                "insufficient_expected_met": 1.0,
                "execution_time_sec": 2.0,
                "source_count": 4,
                "useful_source_count": 3,
                "iterations": 1,
                "claim_count": 5,
                "evidence_count": 5,
            },
        )
    ]
    agg = aggregate_results(results, mode="mock")
    assert agg.n == 1
    assert agg.overall["claim_support_rate"] == 0.8
    assert agg.performance["avg_execution_time"] == 2.0


def test_malformed_evaluation_output_tolerant():
    results = [
        QuestionEvalResult(id="B0", question="q", metrics={"completion_rate": 1.0})
    ]
    agg = aggregate_results(results, mode="mock")
    assert agg.n == 1
    assert "claim_support_rate" in agg.overall


def test_mock_evaluation_smoke():
    agg = run_evaluation(mock=True, ids=["B21"], use_judge=True, save_baseline=False)
    assert agg.n == 1
    assert agg.results[0].metrics.get("numerical_accuracy", 0) == 1.0
