"""Analyst Agent — quantitative analysis with Python; LLM interprets only."""

from __future__ import annotations

from analysis.detect import requires_quantitative_analysis
from analysis.extract import claims_to_datapoints
from analysis.engine import run_quantitative_pipeline
from analysis.validate import validate_datapoints
from prompts import load_prompt
from providers.llm.base import LLMProvider
from schemas.claim import Claim, VerificationStatus, is_reportable_claim
from schemas.report import AnalysisResult, AnalysisType, DataPoint, Dataset
from utils.helpers import safe_json_loads
from utils.logging import get_logger, log_event

logger = get_logger("researchx.agents.analyst")


class AnalystAgent:
    """
    Extract datapoints from claims → normalize/validate → Pandas calculations
    → optional LLM narrative interpretation (never invents numbers).
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.prompt = load_prompt("analyst")

    def analyze(
        self,
        claims: list[Claim],
        research_question: str,
        research_id: str = "",
        *,
        force: bool = False,
    ) -> tuple[list[AnalysisResult], list[DataPoint], Dataset | None]:
        with log_event("analyst", "analyze", research_id=research_id):
            usable = [c for c in claims if is_reportable_claim(c.verification_status)]
            conflicting = [
                c
                for c in claims
                if c.verification_status
                in {VerificationStatus.CONFLICTING, VerificationStatus.CONTRADICTED}
            ]
            pool = usable + conflicting
            if not pool:
                pool = [
                    c
                    for c in claims
                    if c.verification_status
                    not in {
                        VerificationStatus.UNSUPPORTED,
                        VerificationStatus.INSUFFICIENT,
                    }
                ]

            numeric_preview = sum(1 for c in pool if c.value is not None)
            if not force and not requires_quantitative_analysis(research_question, numeric_preview):
                logger.info("[Analyst] Skipped — question does not require quantitative analysis")
                empty = Dataset(name="empty", description="Quantitative analysis not required.")
                return (
                    [
                        AnalysisResult(
                            analysis_type=AnalysisType.INSUFFICIENT_DATA,
                            metric="skipped",
                            calculation="none",
                            interpretation=(
                                "Quantitative analysis skipped: the research question does not "
                                "appear to require numerical calculations."
                            ),
                            status="skipped",
                            confidence=1.0,
                        )
                    ],
                    [],
                    empty,
                )

            points = claims_to_datapoints(pool, reportable_only=False, question=research_question)
            # Prefer reportable; keep conflicting for flags
            if usable:
                preferred_ids = {c.claim_id for c in usable}
                preferred = [p for p in points if p.claim_id in preferred_ids]
                if preferred:
                    points = preferred + [
                        p for p in points if p.claim_id not in preferred_ids and p.flags
                    ]

            points = validate_datapoints(points)
            results, dataset = run_quantitative_pipeline(points)
            results = self._add_interpretations(results, research_question)
            logger.info(
                "[Analyst] %d metrics calculated from %d datapoints",
                len([r for r in results if r.status == "ok"]),
                len(points),
            )
            return results, points, dataset

    def _add_interpretations(
        self,
        results: list[AnalysisResult],
        research_question: str,
    ) -> list[AnalysisResult]:
        computable = [r for r in results if r.status == "ok"]
        if not computable:
            return results
        # Only send calculated numbers — never ask LLM to recompute
        payload = [
            {
                "metric": r.metric,
                "analysis_type": str(r.analysis_type),
                "formula": r.formula,
                "result": r.result,
                "source_ids": r.source_ids,
            }
            for r in computable
        ]
        user = (
            "TASK\nInterpret the ALREADY COMPUTED analysis results. "
            "Do not invent or change any numbers. Mention that values are calculated "
            "from reported source figures when growth rates are discussed.\n\n"
            f"Research question: {research_question}\n\n"
            f"COMPUTED ANALYSIS JSON\n{payload}\n\n"
            "REQUIRED OUTPUT\nJSON with interpretations array: "
            '[{"metric": "...", "interpretation": "..."}]'
        )
        try:
            raw = self.llm.complete(user, system=self.prompt, json_mode=True, temperature=0.2)
            data = safe_json_loads(raw)
            interpretations = {
                str(i.get("metric", "")).lower(): str(i.get("interpretation", ""))
                for i in data.get("interpretations", [])
            }
            for r in results:
                if r.status != "ok":
                    continue
                key = r.metric.lower()
                if key in interpretations:
                    r.interpretation = interpretations[key]
                elif interpretations:
                    r.interpretation = next(iter(interpretations.values()))
                else:
                    r.interpretation = (
                        f"Calculated via {r.formula or r.calculation} from sourced datapoints "
                        f"{r.source_ids}."
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Analyst interpretation failed: %s", exc)
            for r in results:
                if r.status == "ok" and not r.interpretation:
                    r.interpretation = (
                        f"Calculated via {r.formula or r.calculation} from sourced datapoints."
                    )
        return results
