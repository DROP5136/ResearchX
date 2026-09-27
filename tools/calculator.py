"""Safe numeric calculator for analyst agent (no LLM arithmetic)."""

from __future__ import annotations

from typing import Iterable

import numpy as np


class Calculator:
    """Deterministic numeric helpers."""

    @staticmethod
    def pct_change(previous: float, current: float) -> float | None:
        if previous == 0:
            return None
        return ((current - previous) / previous) * 100.0

    @staticmethod
    def yoy_growth(values: list[float]) -> list[float | None]:
        out: list[float | None] = [None]
        for i in range(1, len(values)):
            out.append(Calculator.pct_change(values[i - 1], values[i]))
        return out

    @staticmethod
    def cagr(start: float, end: float, periods: float) -> float | None:
        if start <= 0 or periods <= 0:
            return None
        return (end / start) ** (1.0 / periods) - 1.0

    @staticmethod
    def mean(values: Iterable[float]) -> float | None:
        vals = [float(v) for v in values]
        if not vals:
            return None
        return float(np.mean(vals))

    @staticmethod
    def median(values: Iterable[float]) -> float | None:
        vals = [float(v) for v in values]
        if not vals:
            return None
        return float(np.median(vals))

    @staticmethod
    def min_max(values: Iterable[float]) -> tuple[float | None, float | None]:
        vals = [float(v) for v in values]
        if not vals:
            return None, None
        return float(np.min(vals)), float(np.max(vals))

    @staticmethod
    def percentage_point_diff(a: float, b: float) -> float:
        return float(a - b)

    @staticmethod
    def market_share(part: float, whole: float) -> float | None:
        if whole == 0:
            return None
        return (part / whole) * 100.0

    @staticmethod
    def total(values: Iterable[float]) -> float:
        return float(np.sum(list(values)))

    @staticmethod
    def rank_desc(items: dict[str, float]) -> list[tuple[str, float]]:
        return sorted(items.items(), key=lambda x: x[1], reverse=True)
