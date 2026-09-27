"""Claim helpers."""

from __future__ import annotations

from schemas.claim import Claim, Evidence
from utils.helpers import new_id


def make_evidence(source_id: str, text: str, **kwargs) -> Evidence:
    return Evidence(
        evidence_id=new_id("EVD"),
        source_id=source_id,
        text=text,
        **kwargs,
    )


def make_claim(
    claim_text: str,
    *,
    source_ids: list[str],
    evidence_ids: list[str],
    entity: str | None = None,
    metric: str | None = None,
    value: float | str | None = None,
    unit: str | None = None,
    period: str | None = None,
    confidence: float = 0.5,
) -> Claim:
    return Claim(
        claim_id=new_id("CLM"),
        claim=claim_text,
        source_ids=source_ids,
        evidence_ids=evidence_ids,
        entity=entity,
        metric=metric,
        value=value,
        unit=unit,
        period=period,
        confidence=confidence,
    )
