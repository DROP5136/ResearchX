"""Benchmark runner (calls evaluation.run)."""

from __future__ import annotations

from app.evaluation.run import load_benchmarks, main, run_evaluation

__all__ = ["load_benchmarks", "run_evaluation", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
