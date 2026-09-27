"""Source schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    NEWS = "news"
    INDUSTRY = "industry"
    COMPANY = "company"
    BLOG = "blog"
    FORUM = "forum"
    PDF = "pdf"
    OTHER = "other"


class Source(BaseModel):
    """A collected research source with quality metadata."""

    source_id: str
    url: str = ""
    title: str = ""
    domain: str = ""
    source_type: SourceType = SourceType.OTHER
    published_at: str | None = None
    retrieved_at: datetime | None = None
    content: str = ""
    snippet: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    authority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_primary: bool = False
    task_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Raw search hit before content extraction."""

    title: str = ""
    url: str
    snippet: str = ""
    rank: int = 0
