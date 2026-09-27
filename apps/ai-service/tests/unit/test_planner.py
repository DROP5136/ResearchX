"""Planner agent tests (mocked LLM)."""

from __future__ import annotations

from app.agents.planner import PlannerAgent
from app.providers.llm.mock import MockLLMProvider
from app.schemas.research import ResearchDepth, ResearchQuery


def test_planner_returns_valid_plan():
    agent = PlannerAgent(MockLLMProvider())
    plan = agent.plan(ResearchQuery(query="Analyze the Indian EV market from 2022 to 2026"))
    assert plan.research_goal
    assert plan.subtasks
    assert all(t.task_id and t.question and t.objective for t in plan.subtasks)


def test_planner_no_duplicate_tasks():
    agent = PlannerAgent(MockLLMProvider())
    plan = agent.plan(ResearchQuery(query="Analyze the Indian EV market from 2022 to 2026"))
    questions = [t.question.strip().lower() for t in plan.subtasks]
    assert len(questions) == len(set(questions))


def test_planner_depth_limits():
    agent = PlannerAgent(MockLLMProvider())
    plan = agent.plan(
        ResearchQuery(query="Analyze the Indian EV market", depth=ResearchDepth.QUICK)
    )
    assert len(plan.subtasks) <= 3
