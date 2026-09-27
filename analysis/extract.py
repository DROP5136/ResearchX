"""Extract DataPoints from verified Claims (no invented numbers)."""

from __future__ import annotations

from analysis.normalize import normalize_value, parse_numeric
from schemas.claim import Claim, is_reportable_claim
from schemas.report import DataPoint
from utils.helpers import new_id
from utils.logging import get_logger

logger = get_logger("researchx.analysis.extract")


def claims_to_datapoints(
    claims: list[Claim],
    *,
    reportable_only: bool = True,
    question: str = "",
) -> list[DataPoint]:
    """
    Build DataPoints from structured claim fields.

    Only claims with a parseable numeric value are included.
    Relevance is filtered lightly against the research question tokens.
    """
    q_tokens = {t.lower() for t in (question or "").replace(",", " ").split() if len(t) > 2}
    points: list[DataPoint] = []

    for c in claims:
        if reportable_only and not is_reportable_claim(c.verification_status):
            # Still allow conflicting numeric claims into the store with flags later
            if c.verification_status.value not in {"conflicting", "contradicted"}:
                continue
        if c.value is None:
            continue
        numeric = parse_numeric(c.value)
        if numeric is None:
            continue
        metric = (c.metric or "value").strip()
        # Soft relevance: if question has tokens, prefer overlapping metrics/entities
        if q_tokens:
            blob = f"{metric} {c.entity or ''} {c.claim}".lower()
            if not any(t in blob for t in q_tokens):
                # keep anyway if strongly structured (entity+metric+period)
                if not (c.entity and c.metric and c.period):
                    continue

        if not c.source_ids:
            continue

        norm = normalize_value(numeric, c.unit)
        dp = DataPoint(
            datapoint_id=new_id("DP"),
            metric=metric,
            entity=c.entity,
            value=numeric,
            unit=c.unit,
            period=c.period,
            source_id=c.source_ids[0],
            evidence_id=c.evidence_ids[0] if c.evidence_ids else None,
            claim_id=c.claim_id,
            confidence=c.confidence,
            normalized_value=norm.value,
            normalized_unit=norm.unit,
            normalization_notes=norm.notes,
        )
        points.append(dp)

    logger.info("[Quant] Extracted %d datapoints from %d claims", len(points), len(claims))
    return points
