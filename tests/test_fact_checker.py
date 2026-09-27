"""Fact checker / contradiction tests."""

from __future__ import annotations

from evidence.contradiction import rule_based_candidates
from schemas.claim import Claim, VerificationStatus
from utils.helpers import new_id


def _claim(**kwargs) -> Claim:
    defaults = {
        "claim_id": new_id("CLM"),
        "claim": "test",
        "source_ids": ["SRC_1"],
        "evidence_ids": ["EVD_1"],
        "confidence": 0.7,
        "verification_status": VerificationStatus.UNVERIFIED,
    }
    defaults.update(kwargs)
    return Claim(**defaults)


def test_same_metric_different_values_flagged():
    a = _claim(entity="Tata Motors", metric="market share", period="2024", value=35, unit="%")
    b = _claim(entity="Tata Motors", metric="market share", period="2024", value=29, unit="%")
    pairs = rule_based_candidates([a, b])
    assert len(pairs) == 1


def test_different_periods_not_flagged():
    a = _claim(entity="Tata Motors", metric="market share", period="2023", value=35, unit="%")
    b = _claim(entity="Tata Motors", metric="market share", period="2024", value=29, unit="%")
    pairs = rule_based_candidates([a, b])
    assert pairs == []


def test_different_units_still_compares_numeric():
    # Same unit normalization not applied — values differ → flagged
    a = _claim(entity="India", metric="EV sales", period="2024", value=1500000, unit="vehicles")
    b = _claim(entity="India", metric="EV sales", period="2024", value=1.5, unit="million vehicles")
    pairs = rule_based_candidates([a, b], tolerance=0.05)
    assert len(pairs) == 1
