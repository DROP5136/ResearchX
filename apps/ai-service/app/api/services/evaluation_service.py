"""Thin wrapper around the existing evaluation runner."""

from __future__ import annotations

import json
from typing import Any

from app.api.errors import APIError
from app.api.schemas.research import EvaluationRunRequest
from app.evaluation.run import DASHBOARD_PATH, LATEST_PATH, run_evaluation
from app.utils.logging import get_logger

logger = get_logger("researchx.api.evaluation")


class EvaluationService:
    def run(self, body: EvaluationRunRequest) -> dict[str, Any]:
        try:
            agg = run_evaluation(
                mock=body.mock_mode,
                limit=body.limit,
                ids=body.ids,
                use_judge=body.use_judge,
                save_baseline=body.save_baseline,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Evaluation run failed: %s", exc)
            raise APIError("EVALUATION_FAILED", "Evaluation run failed", status_code=500) from exc

        return {
            "status": "completed",
            "n": agg.n,
            "mode": agg.mode,
            "overall": agg.overall,
            "performance": agg.performance,
        }

    def latest(self) -> dict[str, Any]:
        path = LATEST_PATH if LATEST_PATH.exists() else DASHBOARD_PATH
        if not path.exists():
            raise APIError(
                "EVALUATION_NOT_FOUND",
                "No evaluation results found. Run POST /api/v1/evaluation/run first.",
                status_code=404,
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise APIError(
                "EVALUATION_CORRUPT",
                "Latest evaluation file is malformed",
                status_code=500,
            ) from exc
        # Never expose absolute paths from nested results
        if isinstance(data, dict):
            data.pop("path", None)
        return data
