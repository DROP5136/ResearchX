"""Phase 2 tests: evidence grounding, citations, fact-check, sufficiency, loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.extractor import ExtractorAgent, evidence_supported_by_source
from agents.fact_checker import FactCheckerAgent
from config import Settings
from evidence.citation import validate_claim_traceability, validate_citations
from evidence.contradiction import rule_based_candidates
from evidence.sufficiency import evaluate_sufficiency
from graph.workflow import ResearchWorkflow
from providers.llm.mock import MockLLMProvider
from schemas.claim import Claim, VerificationStatus
from schemas.research import PipelineStatus, ResearchDepth, ResearchPlan, ResearchQuery, ResearchTask
from schemas.source import Source
from utils.helpers import new_id, utc_now


def _claim(**kwargs) -> Claim:
    defaults = {
        "claim_id": new_id("CLM"),
        "claim": "test claim",
        "source_ids": ["SRC_1"],
        "evidence_ids": ["EVD_1"],
        "confidence": 0.7,
        "verification_status": VerificationStatus.UNVERIFIED,
    }
    defaults.update(kwargs)
    return Claim(**defaults)


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        mock_mode=True,
        llm_provider="mock",
        search_provider="duckduckgo",
        cache_path=str(tmp_path / "cache"),
        output_path=str(tmp_path / "outputs"),
        documents_path=str(tmp_path / "documents"),
        chroma_path=str(tmp_path / "chroma"),
        max_sources=10,
        max_research_iterations=1,
        max_concurrent_agents=2,
    )
    for d in (settings.cache_dir, settings.output_dir, settings.documents_dir, settings.chroma_dir):
        d.mkdir(parents=True, exist_ok=True)
    return settings


def test_evidence_must_appear_in_source():
    content = "Company X sold 25000 electric vehicles during Q2 2026."
    assert evidence_supported_by_source(
        "Company X sold 25000 electric vehicles during Q2 2026.", content
    )
    assert not evidence_supported_by_source(
        "Company X increased EV sales by 25%.", content
    )


def test_extractor_rejects_invented_claims():
    agent = ExtractorAgent(MockLLMProvider())
    # Content that does NOT contain the mock LLM's EV sales evidence
    source = Source(
        source_id="SRC_test01",
        url="https://example.com/unrelated",
        title="Unrelated",
        content="Company X launched a new EV model this quarter.",
        retrieved_at=utc_now(),
    )
    claims, evidence = agent.extract_from_source(source, "test")
    # Mock returns EV sales claims whose evidence is not in this content → rejected
    assert claims == []
    assert evidence == []


def test_extractor_associates_source_and_evidence():
    agent = ExtractorAgent(MockLLMProvider())
    source = Source(
        source_id="SRC_test01",
        url="https://example.com/india-ev-sales-fy2024",
        title="EV Sales",
        content=(
            "Indian EV sales reached approximately 1.5 million units in FY2024. "
            "Tata Motors held about 35% of the passenger EV market share in India in 2024. "
            "Tata Motors passenger EV market share was reported at 29% for calendar year 2024. "
            "India EV market size was estimated at USD 3.2 billion in 2022. "
            "India EV market size was estimated at USD 5.1 billion in 2024."
        ),
        retrieved_at=utc_now(),
    )
    claims, evidence = agent.extract_from_source(source, "Analyze Indian EV market")
    assert claims
    assert evidence
    assert all(c.source_ids == ["SRC_test01"] for c in claims)
    assert all(c.evidence_ids for c in claims)
    broken = validate_claim_traceability(claims, [source], evidence)
    assert broken == []


def test_citation_invalid_ids_rejected():
    sources = [
        Source(source_id="SRC_aaa", url="https://example.com/a", title="A"),
    ]
    bad = validate_citations("Claim text [SRC_aaa] and fake [SRC_zzz].", sources)
    assert bad == ["SRC_zzz"]


def test_fact_checker_supported_and_unsupported():
    agent = FactCheckerAgent(MockLLMProvider())
    source = Source(
        source_id="SRC_1",
        url="https://example.com/a",
        title="A",
        content="Company X sold 25000 electric vehicles during Q2 2026.",
    )
    supported = _claim(
        claim="Company X sold 25000 electric vehicles during Q2 2026.",
        source_ids=["SRC_1"],
        evidence_ids=["EVD_1"],
        value=25000,
        entity="Company X",
        metric="EV sales",
        period="Q2 2026",
    )
    unsupported = _claim(
        claim_id=new_id("CLM"),
        claim="Company X increased EV sales by 99%.",
        source_ids=["SRC_1"],
        evidence_ids=["EVD_missing"],
        value=99,
    )
    claims, _, reviews, _ = agent.check(
        [supported, unsupported],
        [source],
        evidence_by_id={"EVD_1": "Company X sold 25000 electric vehicles during Q2 2026."},
        max_iterations=2,
    )
    statuses = {c.claim_id: c.verification_status for c in claims}
    assert statuses[supported.claim_id] in {
        VerificationStatus.SUPPORTED,
        VerificationStatus.PARTIALLY_SUPPORTED,
    }
    assert statuses[unsupported.claim_id] in {
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.INSUFFICIENT,
    }
    assert len(reviews) == 2


def test_contradiction_same_period_different_values():
    a = _claim(entity="Tata Motors", metric="market share", period="2024", value=35, unit="%")
    b = _claim(entity="Tata Motors", metric="market share", period="2024", value=29, unit="%")
    assert len(rule_based_candidates([a, b])) == 1


def test_contradiction_different_periods_not_flagged():
    a = _claim(entity="Tata Motors", metric="market share", period="2023", value=35, unit="%")
    b = _claim(entity="Tata Motors", metric="market share", period="2024", value=29, unit="%")
    assert rule_based_candidates([a, b]) == []


def test_sufficiency_insufficient_triggers_followups():
    plan = ResearchPlan(
        research_goal="Analyze EV market",
        entities=["Company B"],
        metrics=["market share"],
        subtasks=[
            ResearchTask(task_id="T1", question="q", objective="o"),
        ],
    )
    result = evaluate_sufficiency(
        claims=[],
        sources=[],
        contradictions=[],
        plan=plan,
        iteration=0,
        max_iterations=2,
    )
    assert result.is_sufficient is False
    assert result.follow_up_tasks


def test_sufficiency_at_max_iterations_forces_proceed():
    result = evaluate_sufficiency(
        claims=[],
        sources=[],
        contradictions=[],
        plan=None,
        iteration=2,
        max_iterations=2,
    )
    assert result.is_sufficient is True
    assert any("Max research iterations" in r for r in result.reasons)


def test_workflow_terminates_and_writes_evidence_json(mock_settings: Settings):
    workflow = ResearchWorkflow(settings=mock_settings)
    state = workflow.run(
        ResearchQuery(
            query="Analyze the Indian EV market from 2022 to 2026",
            depth=ResearchDepth.QUICK,
        )
    )
    assert state["status"] in {
        PipelineStatus.COMPLETED,
        PipelineStatus.COMPLETED_WITH_LIMITATIONS,
    }
    assert state.get("evidence") is not None
    assert state.get("claims")
    out = Path(state["meta"]["output_dir"])
    for name in (
        "report.md",
        "report.json",
        "sources.json",
        "evidence.json",
        "claims.json",
        "contradictions.json",
        "analysis.json",
        "datapoints.json",
    ):
        assert (out / name).exists(), f"missing {name}"
    assert "Conflicting Evidence" in state["report"].markdown
    assert "Scope & Methodology" in state["report"].markdown


def test_max_iterations_terminates(mock_settings: Settings):
    mock_settings.max_research_iterations = 0
    workflow = ResearchWorkflow(settings=mock_settings)
    state = workflow.run(
        ResearchQuery(query="Analyze the Indian EV market", depth=ResearchDepth.QUICK)
    )
    # iteration never increases when max is 0; must still terminate
    assert state["status"] in {
        PipelineStatus.COMPLETED,
        PipelineStatus.COMPLETED_WITH_LIMITATIONS,
        PipelineStatus.INSUFFICIENT_EVIDENCE,
    }
    assert int(state.get("iteration") or 0) <= mock_settings.max_research_iterations + 1
