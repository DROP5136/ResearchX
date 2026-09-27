"""Statistics helpers for analyst."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def safe_mean(values: Iterable[float]) -> float | None:
    vals = [float(v) for v in values]
    return float(np.mean(vals)) if vals else None


def safe_std(values: Iterable[float]) -> float | None:
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return None
    return float(np.std(vals, ddof=1))
