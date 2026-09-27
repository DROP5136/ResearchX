"""Planner Agent — decomposes a research question into structured subtasks."""

from __future__ import annotations

from pydantic import ValidationError

from app.prompts import load_prompt
from app.providers.llm.base import LLMProvider
from app.schemas.research import ResearchDepth, ResearchPlan, ResearchQuery, ResearchTask
from app.utils.helpers import safe_json_loads
from app.utils.logging import get_logger, log_event

logger = get_logger("researchx.agents.planner")


class PlannerAgent:
    """Create a validated ResearchPlan from a ResearchQuery."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.system_prompt = load_prompt("planner")

    def plan(self, query: ResearchQuery, research_id: str = "") -> ResearchPlan:
        with log_event("planner", "create_plan", research_id=research_id):
            user_prompt = self._build_user_prompt(query)
            raw = self.llm.complete(
                user_prompt,
                system=self.system_prompt,
                json_mode=True,
                temperature=0.1,
            )
            plan = self._parse_and_validate(raw, query)
            plan = self._dedupe_tasks(plan)
            plan = self._enforce_depth_limits(plan, query.depth)
            return plan

    def _build_user_prompt(self, query: ResearchQuery) -> str:
        reqs = "\n".join(f"- {r}" for r in query.requirements) or "- (none)"
        return (
            "TASK\n"
            "Create a structured research plan.\n\n"
            f"Research question: {query.query}\n"
            f"Depth: {query.depth.value}\n"
            f"Requirements:\n{reqs}\n\n"
            "REQUIRED OUTPUT\n"
            "Return JSON matching the schema in the system instructions."
        )

    def _parse_and_validate(self, raw: str, query: ResearchQuery) -> ResearchPlan:
        try:
            data = safe_json_loads(raw)
            # Ensure task objects have required fields
            for i, task in enumerate(data.get("subtasks", [])):
                task.setdefault("task_id", f"T{i + 1}")
                task.setdefault("question", task.get("objective", query.query))
                task.setdefault("objective", task.get("question", query.query))
            plan = ResearchPlan.model_validate(data)
            if not plan.subtasks:
                raise ValueError("Plan has no subtasks")
            return plan
        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning("Plan validation failed (%s); retrying once", exc)
            repair = self.llm.complete(
                (
                    "Repair the following into valid ResearchPlan JSON only.\n"
                    f"Original question: {query.query}\n"
                    f"Invalid response:\n{raw}\n"
                ),
                system=self.system_prompt,
                json_mode=True,
                temperature=0.0,
            )
            data = safe_json_loads(repair)
            for i, task in enumerate(data.get("subtasks", [])):
                task.setdefault("task_id", f"T{i + 1}")
                task.setdefault("question", query.query)
                task.setdefault("objective", "Investigate topic")
            return ResearchPlan.model_validate(data)

    @staticmethod
    def _dedupe_tasks(plan: ResearchPlan) -> ResearchPlan:
        seen: set[str] = set()
        unique: list[ResearchTask] = []
        for task in plan.subtasks:
            key = task.question.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(task)
        # Re-number task ids
        for i, task in enumerate(unique, start=1):
            task.task_id = f"T{i}"
        plan.subtasks = unique
        return plan

    @staticmethod
    def _enforce_depth_limits(plan: ResearchPlan, depth: ResearchDepth) -> ResearchPlan:
        limits = {
            ResearchDepth.QUICK: 3,
            ResearchDepth.STANDARD: 5,
            ResearchDepth.DEEP: 8,
        }
        plan.subtasks = plan.subtasks[: limits.get(depth, 5)]
        return plan
