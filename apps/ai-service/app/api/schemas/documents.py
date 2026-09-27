"""Document processing API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DocumentProcessRequest(BaseModel):
    """Process a PDF already stored on a path visible to the AI service."""

    path: str = Field(..., min_length=1, max_length=1024)
    document_id: str = Field(..., min_length=1, max_length=128)
    original_filename: str | None = Field(default=None, max_length=255)
    force: bool = False

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("path is required")
        # Block crude path traversal attempts in the string itself
        if ".." in cleaned.replace("\\", "/").split("/"):
            raise ValueError("path must not contain '..'")
        return cleaned


class DocumentProcessResponse(BaseModel):
    document_id: str
    status: Literal["ready", "failed"] = "ready"
    page_count: int = 0
    chunk_count: int = 0
    skipped_reembed: bool = False
    stage: str = "completed"
    error: str | None = None
    title: str = ""


class DocumentDeleteRequest(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=128)


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted_chunks: int = 0
