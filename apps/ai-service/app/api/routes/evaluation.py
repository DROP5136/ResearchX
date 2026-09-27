"""Evaluation endpoints — reuse evaluation.run without duplicating metrics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import require_internal_token
from app.api.schemas.research import EvaluationRunRequest, EvaluationRunResponse
from app.api.services.evaluation_service import EvaluationService

router = APIRouter(
    prefix="/api/v1/evaluation",
    tags=["evaluation"],
    dependencies=[Depends(require_internal_token)],
)
_service = EvaluationService()


@router.post("/run", response_model=EvaluationRunResponse, summary="Run evaluation suite")
def run_evaluation(body: EvaluationRunRequest | None = None) -> EvaluationRunResponse:
    payload = body or EvaluationRunRequest()
    data = _service.run(payload)
    return EvaluationRunResponse(**data)


@router.get("/latest", summary="Latest evaluation metrics")
def latest_evaluation() -> dict[str, Any]:
    return _service.latest()
