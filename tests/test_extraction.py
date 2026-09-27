"""Extraction and claim schema tests."""

from __future__ import annotations

from agents.extractor import ExtractorAgent
from providers.llm.mock import MockLLMProvider
from schemas.claim import Claim
from schemas.source import Source
from utils.helpers import utc_now


def test_extractor_produces_claims_with_source_association():
    agent = ExtractorAgent(MockLLMProvider())
    source = Source(
        source_id="SRC_test01",
        url="https://example.com/india-ev-sales-fy2024",
        title="EV Sales",
        content=(
            "Indian EV sales reached approximately 1.5 million units in FY2024. "
            "Tata Motors held about 35% of the passenger EV market share in India in 2024."
        ),
        retrieved_at=utc_now(),
    )
    claims, evidence = agent.extract_from_source(source, "Analyze Indian EV market")
    assert claims
    assert evidence
    assert all(isinstance(c, Claim) for c in claims)
    assert all("SRC_test01" in c.source_ids for c in claims)
    assert all(c.evidence_ids for c in claims)
