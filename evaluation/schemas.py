"""Pydantic models for the evaluation framework."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FailureType(str, Enum):
    RETRIEVAL = "retrieval_failure"
    EXTRACTION = "extraction_failure"
    FACT_CHECKING = "fact_checking_failure"
    CONTRADICTION = "contradiction_failure"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence_failure"
    NUMERICAL = "numerical_analysis_failure"
    CITATION = "citation_failure"
    REPORT = "report_generation_failure"
    HALLUCINATION = "hallucination"
    NONE = "none"


class BenchmarkItem(BaseModel):
    id: str
    question: str
    category: str = "general_factual"
    difficulty: str = "medium"
    expected_subtopics: list[str] = Field(default_factory=list)
    # Back-compat with older field name
    expected_topics: list[str] = Field(default_factory=list)
    expected_claims: list[str] = Field(default_factory=list)
    required_claims: list[str] = Field(default_factory=list)
    preferred_source_types: list[str] = Field(default_factory=list)
    preferred_sources: list[str] = Field(default_factory=list)
    expected_values: dict[str, float] = Field(default_factory=dict)
    expect_contradiction: bool = False
    expect_insufficient: bool = False
    use_synthetic_quant: bool = False
    answer_characteristics: list[str] = Field(default_factory=list)

    def topics(self) -> list[str]:
        return self.expected_subtopics or self.expected_topics

    def claim_hints(self) -> list[str]:
        return self.expected_claims or self.required_claims

    def source_prefs(self) -> list[str]:
        return self.preferred_source_types or self.preferred_sources


class JudgeScores(BaseModel):
    relevance: float = Field(ge=0.0, le=1.0, default=0.0)
    completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    groundedness: float = Field(ge=0.0, le=1.0, default=0.0)
    clarity: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""


class FailureCase(BaseModel):
    question_id: str
    question: str
    failure_type: FailureType
    problematic_claim: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    supporting_evidence: str = ""
    likely_cause: str = ""


class QuestionEvalResult(BaseModel):
    id: str
    question: str
    category: str = ""
    difficulty: str = ""
    completed: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    failures: list[FailureCase] = Field(default_factory=list)
    judge: JudgeScores | None = None
    error: str = ""


class EvalAggregate(BaseModel):
    n: int = 0
    overall: dict[str, float] = Field(default_factory=dict)
    performance: dict[str, float] = Field(default_factory=dict)
    by_category: dict[str, dict[str, float]] = Field(default_factory=dict)
    failures: list[FailureCase] = Field(default_factory=list)
    results: list[QuestionEvalResult] = Field(default_factory=list)
    generated_at: str = ""
    mode: str = "mock"
