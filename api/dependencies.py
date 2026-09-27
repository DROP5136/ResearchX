"""FastAPI dependency helpers."""

from __future__ import annotations

from functools import lru_cache

from config import Settings, get_settings
from api.services.research_service import ResearchService


@lru_cache
def get_research_service() -> ResearchService:
    return ResearchService()


def get_app_settings() -> Settings:
    return get_settings()
