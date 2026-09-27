"""FastAPI entrypoint for ResearchX.

Run (from apps/ai-service):
  uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes import evaluation, health, research
from app.config import get_settings
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ResearchX API",
        description=(
            "HTTP API for the ResearchX multi-agent research pipeline. "
            "This layer orchestrates the existing Python engine — it does not "
            "duplicate research business logic."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    origins = settings.cors_origin_list
    # Only enable CORS when origins are configured. Explicit "*" is allowed if user sets it.
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(research.router)
    app.include_router(evaluation.router)
    return app


app = create_app()
