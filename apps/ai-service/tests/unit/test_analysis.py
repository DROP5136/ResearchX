"""Analyst / calculator tests."""

from __future__ import annotations

from app.tools.calculator import Calculator


def test_yoy_growth():
    yoy = Calculator.yoy_growth([100, 125, 150])
    assert yoy[0] is None
    assert abs(yoy[1] - 25.0) < 1e-9
    assert abs(yoy[2] - 20.0) < 1e-9


def test_division_by_zero():
    assert Calculator.pct_change(0, 10) is None
    assert Calculator.cagr(0, 10, 2) is None


def test_missing_values_mean():
    assert Calculator.mean([]) is None
    assert Calculator.mean([2, 4, 6]) == 4.0


def test_cagr():
    # 100 -> 121 over 2 periods => 10% CAGR
    result = Calculator.cagr(100, 121, 2)
    assert result is not None
    assert abs(result - 0.1) < 1e-9
