"""Research query and task schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResearchDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResearchQuery(BaseModel):
    """User research question with optional constraints."""

    query: str = Field(..., min_length=3)
    depth: ResearchDepth = ResearchDepth.STANDARD
    requirements: list[str] = Field(default_factory=list)
    pdf_paths: list[str] = Field(default_factory=list)


class ResearchTask(BaseModel):
    """A single planned research subtask."""

    task_id: str
    question: str
    objective: str
    priority: int = Field(default=1, ge=1, le=5)
    required_data: list[str] = Field(default_factory=list)
    expected_source_types: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    date_range: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    search_queries: list[str] = Field(default_factory=list)
    notes: str = ""


class ResearchPlan(BaseModel):
    """Structured output from the Planner Agent."""

    research_goal: str
    entities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    date_range: str | None = None
    comparison_dimensions: list[str] = Field(default_factory=list)
    expected_source_types: list[str] = Field(default_factory=list)
    subtasks: list[ResearchTask] = Field(default_factory=list)
    methodology_notes: str = ""


class PipelineStatus(str, Enum):
    INIT = "init"
    PLANNING = "planning"
    RESEARCHING = "researching"
    EXTRACTING = "extracting"
    FACT_CHECKING = "fact_checking"
    NEED_MORE_RESEARCH = "need_more_research"
    ANALYZING = "analyzing"
    WRITING = "writing"
    COMPLETED = "completed"
    COMPLETED_WITH_LIMITATIONS = "completed_with_limitations"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"
