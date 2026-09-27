"""Deterministic mock LLM for offline development and tests."""

from __future__ import annotations

import json
import re

from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Returns deterministic structured responses based on prompt cues."""

    name = "mock"

    def __init__(self, model: str = "mock-model"):
        self.model = model

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        blob = "\n".join(m.content for m in messages).lower()
        # Match on role cues first (most specific → least)
        if "planner agent" in blob or ("create a structured research plan" in blob):
            content = self._plan_response(blob)
        elif "research agent" in blob or "generate search queries" in blob:
            content = json.dumps(
                {
                    "search_queries": [
                        "Indian EV market size 2022 2023 2024",
                        "India electric vehicle sales by year",
                        "Tata Motors EV market share India",
                        "Indian EV policy FAME incentives",
                    ]
                }
            )
        elif "evidence extraction agent" in blob or (
            "extract structured factual claims" in blob
        ):
            content = self._claims_response()
        elif "fact checker agent" in blob or "is_contradiction" in blob:
            content = json.dumps(
                {
                    "is_contradiction": True,
                    "reason": "Both claims report Indian EV market share for overlapping periods with different percentages; definitions may differ.",
                    "possible_explanation": "Different segment definitions (2W vs 4W) or reporting windows.",
                    "verification_notes": "Treat as potential conflict pending period/metric alignment.",
                }
            )
        elif "analyst agent" in blob or "computed analysis" in blob:
            content = json.dumps(
                {
                    "interpretations": [
                        {
                            "metric": "EV sales growth",
                            "interpretation": "Sales show strong year-over-year growth based on structured claim values.",
                        },
                        {
                            "metric": "india:market size",
                            "interpretation": "Market size estimates rose from about USD 3.2B (2022) to USD 5.1B (2024).",
                        },
                        {
                            "metric": "tata motors:market share",
                            "interpretation": "Conflicting share figures (35% vs 29%) suggest definition or source differences.",
                        },
                        {
                            "metric": "market_share_ranking",
                            "interpretation": "Tata Motors appears among leading passenger EV OEMs in the available claims.",
                        },
                    ]
                }
            )
        elif "report writer agent" in blob or "citation-grounded research report" in blob:
            content = self._report_response()
        else:
            content = json.dumps({"message": "Mock LLM response", "ok": True})

        return LLMResponse(content=content, model=self.model, provider=self.name)

    def _plan_response(self, blob: str) -> str:
        query_hint = "research topic"
        m = re.search(r"research question[:\s]+(.+?)(?:\n|$)", blob)
        if m:
            query_hint = m.group(1).strip()[:120]
        return json.dumps(
            {
                "research_goal": f"Analyze: {query_hint}",
                "entities": ["India", "Tata Motors", "Mahindra", "Ola Electric"],
                "metrics": ["market size", "EV sales", "market share", "CAGR"],
                "date_range": "2022-2026",
                "comparison_dimensions": ["manufacturer", "year", "segment"],
                "expected_source_types": ["government", "industry", "news", "company"],
                "methodology_notes": "Mock plan for offline testing",
                "subtasks": [
                    {
                        "task_id": "T1",
                        "question": "What was the Indian EV market size each year from 2022 to 2026?",
                        "objective": "Find historical market size data",
                        "priority": 1,
                        "required_data": ["market size", "year"],
                        "expected_source_types": ["industry", "government"],
                        "entities": ["India"],
                        "metrics": ["market size"],
                        "date_range": "2022-2026",
                    },
                    {
                        "task_id": "T2",
                        "question": "What were EV sales in India by year?",
                        "objective": "Find yearly sales volumes",
                        "priority": 1,
                        "required_data": ["sales", "year"],
                        "expected_source_types": ["industry", "news"],
                        "entities": ["India"],
                        "metrics": ["EV sales"],
                        "date_range": "2022-2026",
                    },
                    {
                        "task_id": "T3",
                        "question": "Which companies had the largest EV market share in India?",
                        "objective": "Compare manufacturers",
                        "priority": 2,
                        "required_data": ["market share", "company"],
                        "expected_source_types": ["industry", "company"],
                        "entities": ["Tata Motors", "Mahindra", "Ola Electric"],
                        "metrics": ["market share"],
                        "date_range": "2022-2026",
                    },
                ],
            }
        )

    def _claims_response(self) -> str:
        return json.dumps(
            {
                "claims": [
                    {
                        "claim": "Indian EV sales reached approximately 1.5 million units in FY2024.",
                        "entity": "India",
                        "metric": "EV sales",
                        "value": 1500000,
                        "unit": "vehicles",
                        "period": "FY2024",
                        "evidence": "Indian EV sales reached approximately 1.5 million units in FY2024.",
                        "confidence": 0.75,
                    },
                    {
                        "claim": "Tata Motors held about 35% of the passenger EV market share in India in 2024.",
                        "entity": "Tata Motors",
                        "metric": "market share",
                        "value": 35,
                        "unit": "%",
                        "period": "2024",
                        "evidence": "Tata Motors held about 35% of the passenger EV market share in India in 2024.",
                        "confidence": 0.7,
                    },
                    {
                        "claim": "Tata Motors passenger EV market share was reported at 29% for calendar year 2024.",
                        "entity": "Tata Motors",
                        "metric": "market share",
                        "value": 29,
                        "unit": "%",
                        "period": "2024",
                        "evidence": "Tata Motors passenger EV market share was reported at 29% for calendar year 2024.",
                        "confidence": 0.65,
                    },
                    {
                        "claim": "India EV market size was estimated at USD 3.2 billion in 2022.",
                        "entity": "India",
                        "metric": "market size",
                        "value": 3.2,
                        "unit": "USD billion",
                        "period": "2022",
                        "evidence": "India EV market size was estimated at USD 3.2 billion in 2022.",
                        "confidence": 0.7,
                    },
                    {
                        "claim": "India EV market size was estimated at USD 5.1 billion in 2024.",
                        "entity": "India",
                        "metric": "market size",
                        "value": 5.1,
                        "unit": "USD billion",
                        "period": "2024",
                        "evidence": "India EV market size was estimated at USD 5.1 billion in 2024.",
                        "confidence": 0.7,
                    },
                ]
            }
        )

    def _report_response(self) -> str:
        return json.dumps(
            {
                "title": "Indian EV Market Analysis (2022-2026)",
                "executive_summary": (
                    "The Indian EV market expanded rapidly between 2022 and 2024, with rising sales "
                    "and competitive manufacturer dynamics. Evidence indicates strong growth in volumes "
                    "and market value, while manufacturer market-share figures show some reporting conflicts "
                    "that require careful interpretation."
                ),
                "methodology": (
                    "This mock report was generated from cached deterministic sources and claims. "
                    "In live mode, the pipeline plans subtasks, searches the web, extracts evidence, "
                    "fact-checks claims, runs quantitative analysis, and writes a citation-grounded report."
                ),
                "key_findings": [
                    "EV sales volumes grew substantially through FY2024.",
                    "Market size estimates rose from about USD 3.2B (2022) to USD 5.1B (2024).",
                    "Manufacturer market-share figures for Tata Motors conflict across sources (35% vs 29%).",
                ],
                "detailed_analysis": (
                    "Structured claims show year-over-year expansion in both sales and market size. "
                    "Quantitative analysis should use Python-computed growth rates rather than LLM arithmetic. "
                    "Contradictions in market share likely stem from segment definitions or reporting windows."
                ),
                "trends": [
                    "Rising EV adoption and market value from 2022-2024",
                    "Intensifying competition among OEMs and two-wheeler EV makers",
                ],
                "contradictions_summary": (
                    "Two sources report different Tata Motors passenger EV market shares for 2024 "
                    "(35% vs 29%). Period and segment definitions should be aligned before drawing conclusions."
                ),
                "limitations": [
                    "Mock mode uses synthetic sources for offline testing.",
                    "Live web data may vary by provider availability and recency.",
                    "Market-share definitions are inconsistent across industry reports.",
                ],
                "conclusion": (
                    "Available evidence supports a growing Indian EV market from 2022-2024, "
                    "with remaining uncertainty around precise manufacturer shares and forward 2025-2026 projections."
                ),
            }
        )
