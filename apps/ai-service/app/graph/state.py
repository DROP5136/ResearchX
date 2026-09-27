"""LangGraph research state definition."""

from __future__ import annotations

from typing import Any, TypedDict

from app.schemas.claim import Claim, ClaimSupportResult, Contradiction, Evidence
from app.schemas.report import AnalysisResult, DataPoint, Dataset, ResearchReport
from app.schemas.research import PipelineStatus, ResearchPlan, ResearchQuery, ResearchTask
from app.schemas.source import Source


class ResearchState(TypedDict, total=False):
    """Shared state flowing through the ResearchX LangGraph workflow."""

    research_id: str
    query: ResearchQuery
    plan: ResearchPlan | None
    tasks: list[ResearchTask]
    follow_up_tasks: list[ResearchTask]
    sources: list[Source]
    evidence: list[Evidence]
    claims: list[Claim]
    claim_reviews: list[ClaimSupportResult]
    contradictions: list[Contradiction]
    datapoints: list[DataPoint]
    dataset: Dataset | None
    analysis: list[AnalysisResult]
    report: ResearchReport | None
    iteration: int
    max_iterations: int
    need_more_research: bool
    sufficiency_reasons: list[str]
    completed_with_limitations: bool
    status: PipelineStatus
    errors: list[str]
    progress: list[str]
    pdf_document_ids: list[str]
    meta: dict[str, Any]
