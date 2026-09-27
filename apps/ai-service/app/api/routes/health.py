"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_app_settings
from app.api.schemas.common import HealthResponse
from app.config import Settings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health",
    description="Lightweight liveness check. Never exposes secrets.",
)
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    providers = {
        "llm": "mock" if settings.mock_mode else settings.llm_provider,
        "search": settings.search_provider,
        "groq_keys_configured": len(settings.groq_api_keys),
        "gemini_configured": bool(settings.gemini_api_key),
        "mock_mode": settings.mock_mode,
    }
    return HealthResponse(
        status="ok",
        service="researchx",
        version=settings.app_version,
        environment=settings.app_env,
        providers=providers,
    )
