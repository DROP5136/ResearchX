"""Evaluation endpoints — reuse evaluation.run without duplicating metrics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.schemas.research import EvaluationRunRequest, EvaluationRunResponse
from app.api.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])
_service = EvaluationService()


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    summary="Run evaluation suite",
    description="Runs the existing evaluation framework. Prefer mock_mode=true in CI.",
)
def run_evaluation(body: EvaluationRunRequest | None = None) -> EvaluationRunResponse:
    payload = body or EvaluationRunRequest()
    data = _service.run(payload)
    return EvaluationRunResponse(**data)


@router.get(
    "/latest",
    summary="Latest evaluation metrics",
    description="Returns evaluation/results/latest.json (dashboard-ready).",
)
def latest_evaluation() -> dict[str, Any]:
    return _service.latest()
