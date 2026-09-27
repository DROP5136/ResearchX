"""
ResearchX evaluation runner.

Usage:
  python -m evaluation.run --mock
  python -m evaluation.run --mock --limit 5
  python -m evaluation.run --mock --judge
  python -m evaluation.run --mock --save-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_settings
from evaluation.failures import classify_failures
from evaluation.judge import LLMJudge
from evaluation.metrics import evaluate_run
from evaluation.regression import compare_aggregates
from evaluation.report import to_dashboard_json, write_markdown_report
from evaluation.schemas import BenchmarkItem, EvalAggregate, QuestionEvalResult
from graph.workflow import ResearchWorkflow
from providers.llm import get_llm_provider
from schemas.report import AnalysisResult, AnalysisType
from schemas.research import PipelineStatus, ResearchDepth, ResearchQuery
from tools.calculator import Calculator
from utils.logging import get_logger, setup_logging

logger = get_logger("researchx.eval")

EVAL_DIR = Path(__file__).parent
BENCHMARKS_PATH = EVAL_DIR / "benchmarks.json"
RESULTS_DIR = EVAL_DIR / "results"
LATEST_PATH = RESULTS_DIR / "latest.json"
BASELINE_PATH = RESULTS_DIR / "baseline.json"
DASHBOARD_PATH = RESULTS_DIR / "dashboard.json"
REPORT_PATH = RESULTS_DIR / "evaluation_report.md"


def load_benchmarks(path: Path | None = None) -> list[BenchmarkItem]:
    raw = json.loads((path or BENCHMARKS_PATH).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Benchmarks file must be a JSON array")
    return [BenchmarkItem.model_validate(item) for item in raw]


def _synthetic_yoy_analysis() -> list[AnalysisResult]:
    """Deterministic gold analysis for DemoCo 100/120/150 (independent of LLM)."""
    values = [100.0, 120.0, 150.0]
    yoy = Calculator.yoy_growth(values)
    return [
        AnalysisResult(
            analysis_type=AnalysisType.YOY,
            metric="DemoCo YoY growth",
            calculation="yoy_growth([100, 120, 150])",
            formula="(current - previous) / previous * 100",
            result={"values": values, "yoy_pct": yoy, "periods": ["2022", "2023", "2024"]},
            values=values,
            interpretation="Synthetic evaluation series for deterministic arithmetic checks",
            status="ok",
            source_ids=["SRC_synthetic"],
        )
    ]


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _mean_metric(results: list[QuestionEvalResult], key: str) -> float:
    vals = [
        float(r.metrics[key])
        for r in results
        if isinstance(r.metrics.get(key), (int, float))
    ]
    return _avg(vals)


def aggregate_results(
    results: list[QuestionEvalResult],
    *,
    mode: str,
) -> EvalAggregate:
    overall_keys = [
        "completion_rate",
        "claim_support_rate",
        "citation_coverage",
        "citation_correctness",
        "citation_completeness",
        "hallucination_rate",
        "fabricated_number_rate",
        "topic_coverage",
        "claim_hint_coverage",
        "source_relevance",
        "source_diversity",
        "duplicate_source_rate",
        "evidence_coverage",
        "evidence_relevance",
        "evidence_completeness",
        "evidence_traceability",
        "numerical_accuracy",
        "unsupported_rate",
        "conflicting_rate",
        "contradiction_expectation_met",
        "insufficient_expected_met",
    ]
    overall = {k: _mean_metric(results, k) for k in overall_keys}
    performance = {
        "avg_execution_time": _mean_metric(results, "execution_time_sec"),
        "avg_sources": _mean_metric(results, "source_count"),
        "avg_useful_sources": _mean_metric(results, "useful_source_count"),
        "avg_iterations": _mean_metric(results, "iterations"),
        "avg_claims": _mean_metric(results, "claim_count"),
        "avg_evidence": _mean_metric(results, "evidence_count"),
    }

    by_category: dict[str, dict[str, float]] = {}
    cats = sorted({r.category for r in results if r.category})
    for cat in cats:
        subset = [r for r in results if r.category == cat]
        by_category[cat] = {
            "n": float(len(subset)),
            "claim_support_rate": _mean_metric(subset, "claim_support_rate"),
            "citation_correctness": _mean_metric(subset, "citation_correctness"),
            "hallucination_rate": _mean_metric(subset, "hallucination_rate"),
            "topic_coverage": _mean_metric(subset, "topic_coverage"),
        }

    failures = [f for r in results for f in r.failures]
    return EvalAggregate(
        n=len(results),
        overall=overall,
        performance=performance,
        by_category=by_category,
        failures=failures,
        results=results,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
    )


def evaluate_question(
    item: BenchmarkItem,
    *,
    settings,
    judge: LLMJudge | None = None,
) -> QuestionEvalResult:
    start = time.perf_counter()
    workflow = ResearchWorkflow(settings=settings)
    query = ResearchQuery(query=item.question, depth=ResearchDepth.QUICK)
    try:
        state = workflow.run(query)
        status = state.get("status")
        completed = bool(
            status
            and status
            in {
                PipelineStatus.COMPLETED,
                PipelineStatus.COMPLETED_WITH_LIMITATIONS,
                PipelineStatus.INSUFFICIENT_EVIDENCE,
            }
        )
        analysis = list(state.get("analysis") or [])
        if item.use_synthetic_quant:
            # Gold arithmetic path — do not trust LLM for expected YoY values
            analysis = _synthetic_yoy_analysis() + analysis

        meta = state.get("meta") or {}
        metrics = evaluate_run(
            completed=completed,
            report=state.get("report"),
            sources=state.get("sources") or [],
            claims=state.get("claims") or [],
            contradictions=state.get("contradictions") or [],
            evidence=state.get("evidence") or [],
            analysis=analysis,
            datapoints=state.get("datapoints") or [],
            question=item.question,
            expected_topics=item.topics(),
            expected_claims=item.claim_hints(),
            expected_values=item.expected_values,
            expect_contradiction=item.expect_contradiction,
            expect_insufficient=item.expect_insufficient,
            duration_sec=time.perf_counter() - start,
            iterations=int(state.get("iteration") or 0),
            stage_timings=meta.get("stage_timings") or {},
            llm_calls=meta.get("llm_calls"),
            token_usage=meta.get("token_usage"),
            estimated_cost=meta.get("estimated_cost"),
        )
        failures = classify_failures(
            question_id=item.id,
            question=item.question,
            metrics=metrics,
            expect_contradiction=item.expect_contradiction,
            expect_insufficient=item.expect_insufficient,
        )
        judge_scores = None
        if judge is not None:
            judge_scores = judge.judge(
                question=item.question,
                report=state.get("report"),
                claims=state.get("claims") or [],
                sources=state.get("sources") or [],
            )
        return QuestionEvalResult(
            id=item.id,
            question=item.question,
            category=item.category,
            difficulty=item.difficulty,
            completed=completed,
            metrics=metrics,
            failures=failures,
            judge=judge_scores,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Benchmark %s failed", item.id)
        metrics = {
            "completed": False,
            "completion_rate": 0.0,
            "error": str(exc),
            "execution_time_sec": round(time.perf_counter() - start, 3),
            "source_count": 0,
            "claim_count": 0,
            "claim_support_rate": 0.0,
            "citation_correctness": 0.0,
            "hallucination_rate": 1.0,
            "topic_coverage": 0.0,
            "iterations": 0,
        }
        failures = classify_failures(
            question_id=item.id,
            question=item.question,
            metrics=metrics,
            expect_contradiction=item.expect_contradiction,
            expect_insufficient=item.expect_insufficient,
        )
        return QuestionEvalResult(
            id=item.id,
            question=item.question,
            category=item.category,
            difficulty=item.difficulty,
            completed=False,
            metrics=metrics,
            failures=failures,
            error=str(exc),
        )


def run_evaluation(
    *,
    mock: bool = True,
    limit: int | None = None,
    ids: list[str] | None = None,
    use_judge: bool = False,
    save_baseline: bool = False,
    benchmarks_path: Path | None = None,
) -> EvalAggregate:
    setup_logging()
    get_settings.cache_clear()
    settings = get_settings()
    if mock:
        settings.mock_mode = True

    items = load_benchmarks(benchmarks_path)
    if ids:
        wanted = set(ids)
        items = [i for i in items if i.id in wanted]
    if limit:
        items = items[:limit]

    judge = None
    if use_judge:
        llm = get_llm_provider(settings)
        judge = LLMJudge(llm=llm)

    mode = "mock" if mock else "live"
    logger.info("Running evaluation mode=%s n=%d judge=%s", mode, len(items), use_judge)

    results: list[QuestionEvalResult] = []
    for item in items:
        logger.info("[%s] %s", item.id, item.question[:80])
        results.append(evaluate_question(item, settings=settings, judge=judge))

    agg = aggregate_results(results, mode=mode)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    dashboard = to_dashboard_json(agg)
    LATEST_PATH.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    DASHBOARD_PATH.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")

    baseline = None
    if BASELINE_PATH.exists():
        try:
            baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            baseline = None

    write_markdown_report(agg, REPORT_PATH, baseline=baseline)

    if save_baseline:
        BASELINE_PATH.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
        logger.info("Saved baseline → %s", BASELINE_PATH)

    if baseline:
        rows = compare_aggregates(baseline, dashboard)
        logger.info("Regression rows: %d", len(rows))

    return agg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ResearchX evaluation & benchmarking")
    parser.add_argument("--mock", action="store_true", default=True, help="Mock mode (default)")
    parser.add_argument("--live", action="store_true", help="Use live LLM/search providers")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", type=str, default="", help="Comma-separated benchmark IDs")
    parser.add_argument("--judge", action="store_true", help="Enable optional LLM-as-judge")
    parser.add_argument("--save-baseline", action="store_true", help="Write current results as baseline")
    parser.add_argument("--benchmarks", type=str, default="", help="Alternate benchmarks JSON path")
    args = parser.parse_args(argv)

    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or None
    path = Path(args.benchmarks) if args.benchmarks else None
    agg = run_evaluation(
        mock=not args.live,
        limit=args.limit,
        ids=ids,
        use_judge=args.judge,
        save_baseline=args.save_baseline,
        benchmarks_path=path,
    )
    print(json.dumps({"n": agg.n, "overall": agg.overall, "performance": agg.performance}, indent=2))
    print(f"\nWrote {LATEST_PATH}")
    print(f"Wrote {DASHBOARD_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
