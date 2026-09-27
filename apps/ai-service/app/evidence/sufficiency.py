"""Evidence sufficiency evaluation for the research loop."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.claim import (
    Claim,
    Contradiction,
    VerificationStatus,
    is_conflicting_status,
    is_unsupported_status,
)
from app.schemas.research import ResearchPlan, ResearchTask
from app.schemas.source import Source
from app.utils.helpers import new_id


@dataclass
class SufficiencyResult:
    """Outcome of the evidence-sufficiency decision."""

    is_sufficient: bool
    reasons: list[str] = field(default_factory=list)
    follow_up_tasks: list[ResearchTask] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


def evaluate_sufficiency(
    *,
    claims: list[Claim],
    sources: list[Source],
    contradictions: list[Contradiction],
    plan: ResearchPlan | None,
    iteration: int,
    max_iterations: int,
) -> SufficiencyResult:
    """
    Decide whether evidence is sufficient to proceed to analysis.

    Does NOT invent facts — only inspects structured state.
    """
    reasons: list[str] = []
    supported = [
        c
        for c in claims
        if c.verification_status
        in {VerificationStatus.SUPPORTED, VerificationStatus.PARTIALLY_SUPPORTED}
    ]
    unsupported = [c for c in claims if is_unsupported_status(c.verification_status)]
    conflicting = [c for c in claims if is_conflicting_status(c.verification_status)]
    open_conflicts = [
        c for c in contradictions if c.is_true_contradiction and c.status.value in {"open", "unresolved"}
    ]

    domains = {s.domain for s in sources if s.domain}
    stats = {
        "claims": len(claims),
        "supported": len(supported),
        "unsupported": len(unsupported),
        "conflicting": len(conflicting),
        "sources": len(sources),
        "domains": len(domains),
        "open_conflicts": len(open_conflicts),
    }

    # Hard stop: always sufficient once max iterations reached (caller handles limitations)
    if iteration >= max_iterations:
        return SufficiencyResult(
            is_sufficient=True,
            reasons=["Max research iterations reached; proceeding with limitations."],
            stats=stats,
        )

    insufficient = False
    if len(claims) < 3:
        insufficient = True
        reasons.append(f"Too few claims extracted ({len(claims)} < 3).")
    if len(supported) < 2:
        insufficient = True
        reasons.append(f"Too few supported claims ({len(supported)} < 2).")
    if claims and len(unsupported) > max(1, len(claims) // 2):
        insufficient = True
        reasons.append("Majority of claims are unsupported.")
    if len(sources) < 2:
        insufficient = True
        reasons.append(f"Insufficient source diversity ({len(sources)} sources).")
    if len(domains) < 2 and len(sources) >= 2:
        reasons.append("Sources lack domain diversity.")
        # soft signal — only force more research if also few supported
        if len(supported) < 3:
            insufficient = True
    if len(open_conflicts) >= 3:
        insufficient = True
        reasons.append(f"Many unresolved conflicts ({len(open_conflicts)}).")

    # Gap-driven follow-ups from plan entities/metrics with weak coverage
    follow_ups: list[ResearchTask] = []
    if insufficient and plan:
        covered_entities = {
            (c.entity or "").strip().lower() for c in supported if c.entity
        }
        covered_metrics = {
            (c.metric or "").strip().lower() for c in supported if c.metric
        }
        for entity in plan.entities:
            if entity.lower() not in covered_entities:
                follow_ups.append(
                    ResearchTask(
                        task_id=new_id("FT"),
                        question=(
                            f"Find reliable data for {entity} related to: {plan.research_goal}. "
                            "Prefer primary or reputable industry/government sources."
                        ),
                        objective=f"Fill evidence gap for entity {entity}",
                        priority=1,
                        entities=[entity],
                        metrics=plan.metrics[:3],
                        date_range=plan.date_range,
                        notes="follow_up_gap",
                    )
                )
        for metric in plan.metrics:
            if metric.lower() not in covered_metrics:
                follow_ups.append(
                    ResearchTask(
                        task_id=new_id("FT"),
                        question=(
                            f"Find numerical evidence for metric '{metric}' "
                            f"regarding: {plan.research_goal}."
                        ),
                        objective=f"Fill evidence gap for metric {metric}",
                        priority=1,
                        entities=plan.entities[:3],
                        metrics=[metric],
                        date_range=plan.date_range,
                        notes="follow_up_gap",
                    )
                )
        follow_ups = follow_ups[:3]

    if not reasons and not insufficient:
        reasons.append("Evidence coverage meets minimum sufficiency thresholds.")

    return SufficiencyResult(
        is_sufficient=not insufficient,
        reasons=reasons,
        follow_up_tasks=follow_ups,
        stats=stats,
    )
