"""FastAPI entrypoint for ResearchX.

Run (from apps/ai-service):
  uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes import documents, evaluation, health, research
from app.config import get_settings
from app.utils.logging import setup_logging


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    is_prod = (settings.app_env or "").lower() == "production"
    app = FastAPI(
        title="ResearchX API",
        description=(
            "HTTP API for the ResearchX multi-agent research pipeline. "
            "This layer orchestrates the existing Python engine — it does not "
            "duplicate research business logic."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
    )

    origins = settings.cors_origin_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(research.router)
    app.include_router(documents.router)
    app.include_router(evaluation.router)
    return app


app = create_app()
