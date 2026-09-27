"""Evaluation package — metrics, benchmarks, runner, regression."""

from app.evaluation.metrics import evaluate_run
from app.evaluation.run import load_benchmarks, run_evaluation

__all__ = ["evaluate_run", "load_benchmarks", "run_evaluation"]
