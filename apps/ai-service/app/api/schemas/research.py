"""Research API request/response schemas (thin DTOs over pipeline artifacts)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ResearchCreateRequest(BaseModel):
    """Start a new research job against the existing ResearchX pipeline."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        examples=["Analyze the Indian EV market from 2022 to 2026"],
    )
    depth: Literal["quick", "standard", "deep"] = "standard"
    max_iterations: int | None = Field(default=None, ge=0, le=5)
    enable_web_search: bool = True
    enable_pdf_rag: bool = False
    enable_document_research: bool = False
    enable_analysis: bool = True
    mock_mode: bool | None = None
    requirements: list[str] = Field(default_factory=list, max_length=20)
    pdf_paths: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Optional local PDF paths for hybrid RAG",
    )
    document_ids: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Stable document IDs already indexed via /api/v1/documents/process",
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned

    @field_validator("requirements")
    @classmethod
    def limit_requirement_length(cls, v: list[str]) -> list[str]:
        out = []
        for item in v:
            text = (item or "").strip()
            if text:
                out.append(text[:500])
        return out


class ResearchStartResponse(BaseModel):
    research_id: str
    status: str = "queued"


class ResearchStatusResponse(BaseModel):
    research_id: str
    status: str
    current_stage: str | None = None
    progress: int = Field(default=0, ge=0, le=100)
    message: str | None = None
    errors: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0


class ResearchListItem(BaseModel):
    research_id: str
    query: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    current_stage: str | None = None


class ResearchListResponse(BaseModel):
    items: list[ResearchListItem]
    total: int
    limit: int
    offset: int


class SourceOut(BaseModel):
    source_id: str
    title: str = ""
    url: str = ""
    domain: str = ""
    published_at: str | None = None
    source_type: str | None = None
    relevance_score: float | None = None
    quality_score: float | None = None
    authority_score: float | None = None
    snippet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimOut(BaseModel):
    claim_id: str
    claim: str
    verification_status: str | None = None
    confidence: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    contradiction_status: str | None = None
    notes: str = ""


class ReportOut(BaseModel):
    research_id: str
    title: str = ""
    query: str = ""
    executive_summary: str = ""
    methodology: str = ""
    key_findings: list[str] = Field(default_factory=list)
    detailed_analysis: str = ""
    sections: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    analysis: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conclusion: str = ""
    markdown: str = ""
    status_note: str = ""


class ResearchResultResponse(BaseModel):
    research_id: str
    query: str = ""
    status: str
    current_stage: str | None = None
    progress: int = 0
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    analysis: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunRequest(BaseModel):
    mock_mode: bool = True
    limit: int | None = Field(default=None, ge=1, le=50)
    ids: list[str] | None = None
    use_judge: bool = False
    save_baseline: bool = False


class EvaluationRunResponse(BaseModel):
    status: str = "completed"
    n: int = 0
    mode: str = "mock"
    overall: dict[str, Any] = Field(default_factory=dict)
    performance: dict[str, Any] = Field(default_factory=dict)
