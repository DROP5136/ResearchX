"""End-to-end workflow test with mock providers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.graph.workflow import ResearchWorkflow
from app.schemas.research import PipelineStatus, ResearchDepth, ResearchQuery


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


def test_mock_end_to_end_workflow(mock_settings: Settings):
    workflow = ResearchWorkflow(settings=mock_settings)
    query = ResearchQuery(
        query="Analyze the Indian EV market from 2022 to 2026",
        depth=ResearchDepth.QUICK,
    )
    state = workflow.run(query)

    assert state["status"] in {
        PipelineStatus.COMPLETED,
        PipelineStatus.COMPLETED_WITH_LIMITATIONS,
    }
    assert state.get("plan") is not None
    assert state.get("sources")
    assert state.get("claims")
    assert state.get("report") is not None
    assert state["report"].markdown
    assert "References" in state["report"].markdown

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
