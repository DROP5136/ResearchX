"""Health and readiness check routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_app_settings
from app.api.schemas.common import HealthResponse, ReadyResponse
from app.config import Settings
from app.storage import redis_client

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service liveness",
    description="Lightweight liveness check. Never exposes secrets.",
)
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    providers = {
        "llm": "mock" if settings.mock_mode else settings.llm_provider,
        "search": settings.search_provider,
        "groq_keys_configured": len(settings.groq_api_keys),
        "gemini_configured": bool(settings.gemini_api_key),
        "mock_mode": settings.mock_mode,
        "redis_configured": bool((settings.redis_url or "").strip()),
    }
    return HealthResponse(
        status="ok",
        service="researchx-ai",
        version=settings.app_version,
        environment=settings.app_env,
        providers=providers,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Service readiness",
    description="Checks optional dependencies. Redis failure does not mark the service not-ready.",
)
def ready(response: Response, settings: Settings = Depends(get_app_settings)) -> ReadyResponse:
    redis_ok = redis_client.redis_ping() if (settings.redis_url or "").strip() else None
    data_ok = settings.output_dir.exists() and settings.cache_dir.exists()
    # AI service is ready if local storage is writable; Redis is optional.
    status = "ready" if data_ok else "not_ready"
    if status != "ready":
        response.status_code = 503
    return ReadyResponse(
        status=status,
        service="researchx-ai",
        checks={
            "data_dirs": data_ok,
            "redis": redis_ok,
            "redis_optional": True,
        },
    )
