"""FastAPI dependency helpers."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Header, Request

from app.api.errors import APIError
from app.api.services.research_service import ResearchService
from app.config import Settings, get_settings


@lru_cache
def get_research_service() -> ResearchService:
    return ResearchService()


def get_app_settings() -> Settings:
    return get_settings()


def require_internal_token(
    request: Request,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """
    Require shared secret for AI service routes when AI_SERVICE_TOKEN is configured.
    In production (app_env=production), an empty token is rejected.
    Health checks should not use this dependency.
    """
    settings = get_settings()
    expected = (settings.ai_service_token or "").strip()
    is_prod = (settings.app_env or "").lower() == "production"

    if not expected:
        if is_prod:
            raise APIError(
                "MISCONFIGURED",
                "AI service token is required in production",
                status_code=503,
            )
        # Development convenience: allow open FastAPI when token unset
        return

    provided = (x_internal_token or "").strip()
    # Also accept Authorization: Bearer <token> for flexibility
    if not provided:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()

    if not provided or provided != expected:
        raise APIError("UNAUTHORIZED", "Invalid or missing internal service token", status_code=401)
