"""API exception types and FastAPI exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.logging import get_logger

logger = get_logger("researchx.api")


class APIError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ResearchNotFoundError(APIError):
    def __init__(self, research_id: str):
        super().__init__(
            "RESEARCH_NOT_FOUND",
            "Research session not found",
            status_code=404,
            details={"research_id": research_id},
        )


class PipelineFailureError(APIError):
    def __init__(self, message: str = "Research pipeline failed"):
        super().__init__("PIPELINE_FAILURE", message, status_code=500)


class ProviderFailureError(APIError):
    def __init__(self, message: str = "Upstream provider failure"):
        super().__init__("PROVIDER_FAILURE", message, status_code=502)


class TimeoutErrorAPI(APIError):
    def __init__(self, message: str = "Research timed out"):
        super().__init__("TIMEOUT", message, status_code=504)


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        logger.warning("API error %s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Avoid leaking internal locations excessively; keep structured detail for clients
        safe_details = []
        for err in exc.errors():
            safe_details.append(
                {
                    "loc": [str(x) for x in err.get("loc", ())],
                    "msg": err.get("msg"),
                    "type": err.get("type"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "INVALID_REQUEST",
                "Request validation failed",
                {"errors": safe_details},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "An unexpected server error occurred"),
        )
