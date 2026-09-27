"""Claim and evidence schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Claim verification states (Phase 2)."""

    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"
    STALE = "stale"
    # Legacy aliases kept for backward compatibility with earlier runs/tests
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


class Evidence(BaseModel):
    """A passage extracted from a source that supports a claim."""

    evidence_id: str
    source_id: str
    text: str
    page: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    chunk_id: str | None = None
    document_id: str | None = None


class Claim(BaseModel):
    """A structured factual claim grounded in evidence."""

    claim_id: str
    claim: str
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    entity: str | None = None
    metric: str | None = None
    value: float | str | None = None
    unit: str | None = None
    period: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: str = ""
    verification_reason: str = ""


class ClaimSupportResult(BaseModel):
    """Structured fact-check outcome for one claim."""

    claim_id: str
    status: VerificationStatus
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""


class ContradictionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    EXPLAINED = "explained"
    DISMISSED = "dismissed"


class Contradiction(BaseModel):
    """A detected conflict between claims."""

    contradiction_id: str
    claim_ids: list[str]
    description: str
    sources: list[str] = Field(default_factory=list)
    possible_explanation: str = ""
    status: ContradictionStatus = ContradictionStatus.OPEN
    is_true_contradiction: bool | None = None


class ExtractedClaimBatch(BaseModel):
    """LLM extraction output wrapper."""

    claims: list[dict[str, Any]] = Field(default_factory=list)


def is_reportable_claim(status: VerificationStatus) -> bool:
    """Claims safe to present as established findings."""
    return status in {
        VerificationStatus.SUPPORTED,
        VerificationStatus.PARTIALLY_SUPPORTED,
    }


def is_conflicting_status(status: VerificationStatus) -> bool:
    return status in {
        VerificationStatus.CONFLICTING,
        VerificationStatus.CONTRADICTED,
    }


def is_unsupported_status(status: VerificationStatus) -> bool:
    return status in {
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.INSUFFICIENT,
    }
