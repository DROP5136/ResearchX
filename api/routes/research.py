"""Research REST endpoints — thin wrappers around ResearchService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_research_service
from api.schemas.research import (
    ClaimOut,
    ReportOut,
    ResearchCreateRequest,
    ResearchListResponse,
    ResearchResultResponse,
    ResearchStartResponse,
    ResearchStatusResponse,
    SourceOut,
)
from api.services.research_service import ResearchService

router = APIRouter(prefix="/api/v1/research", tags=["research"])


@router.post(
    "",
    response_model=ResearchStartResponse,
    status_code=202,
    summary="Start research",
    description=(
        "Queue a research job. The existing ResearchX LangGraph pipeline runs in a "
        "background thread. Poll `/status` then fetch the result."
    ),
)
def start_research(
    body: ResearchCreateRequest,
    service: ResearchService = Depends(get_research_service),
) -> ResearchStartResponse:
    data = service.start_research(body)
    return ResearchStartResponse(**data)


@router.get(
    "",
    response_model=ResearchListResponse,
    summary="List research sessions",
)
def list_research(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status, e.g. completed"),
    service: ResearchService = Depends(get_research_service),
) -> ResearchListResponse:
    data = service.list_research(limit=limit, offset=offset, status=status)
    return ResearchListResponse(**data)


@router.get(
    "/{research_id}",
    response_model=ResearchResultResponse,
    summary="Get research result",
)
def get_research(
    research_id: str,
    service: ResearchService = Depends(get_research_service),
) -> ResearchResultResponse:
    data = service.get_result(research_id)
    return ResearchResultResponse(**data)


@router.get(
    "/{research_id}/status",
    response_model=ResearchStatusResponse,
    summary="Get research status",
)
def get_status(
    research_id: str,
    service: ResearchService = Depends(get_research_service),
) -> ResearchStatusResponse:
    data = service.get_status(research_id)
    return ResearchStatusResponse(**data)


@router.get(
    "/{research_id}/sources",
    response_model=list[SourceOut],
    summary="List sources for a research session",
)
def get_sources(
    research_id: str,
    service: ResearchService = Depends(get_research_service),
) -> list[SourceOut]:
    return [SourceOut(**row) for row in service.get_sources(research_id)]


@router.get(
    "/{research_id}/claims",
    response_model=list[ClaimOut],
    summary="List claims for a research session",
)
def get_claims(
    research_id: str,
    service: ResearchService = Depends(get_research_service),
) -> list[ClaimOut]:
    return [ClaimOut(**row) for row in service.get_claims(research_id)]


@router.get(
    "/{research_id}/report",
    response_model=ReportOut,
    summary="Get citation-grounded report",
)
def get_report(
    research_id: str,
    service: ResearchService = Depends(get_research_service),
) -> ReportOut:
    return ReportOut(**service.get_report(research_id))
