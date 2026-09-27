"""Evidence package."""

from app.evidence.citation import (
    build_references,
    citation_tag,
    claims_with_citations,
    validate_citations,
    validate_claim_traceability,
)
from app.evidence.claim import make_claim, make_evidence
from app.evidence.contradiction import detect_contradictions, rule_based_candidates
from app.evidence.source import classify_source_type, enrich_source, score_source
from app.evidence.sufficiency import SufficiencyResult, evaluate_sufficiency

__all__ = [
    "SufficiencyResult",
    "build_references",
    "citation_tag",
    "claims_with_citations",
    "classify_source_type",
    "detect_contradictions",
    "enrich_source",
    "evaluate_sufficiency",
    "make_claim",
    "make_evidence",
    "rule_based_candidates",
    "score_source",
    "validate_citations",
    "validate_claim_traceability",
]
