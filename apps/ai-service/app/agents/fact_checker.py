"""Fact Checker Agent — verify claim support and detect contradictions."""

from __future__ import annotations

import re

from app.evidence.contradiction import detect_contradictions
from app.evidence.sufficiency import SufficiencyResult, evaluate_sufficiency
from app.prompts import load_prompt
from app.providers.llm.base import LLMProvider
from app.schemas.claim import (
    Claim,
    ClaimSupportResult,
    Contradiction,
    Evidence,
    VerificationStatus,
    is_conflicting_status,
    is_unsupported_status,
)
from app.schemas.research import ResearchPlan
from app.schemas.source import Source
from app.utils.logging import get_logger, log_event

logger = get_logger("researchx.agents.fact_checker")


class FactCheckerAgent:
    """Verify claim support and find contradictions."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.prompt = load_prompt("fact_checker")

    def check(
        self,
        claims: list[Claim],
        sources: list[Source],
        evidence_by_id: dict[str, str] | None = None,
        evidence_list: list[Evidence] | None = None,
        plan: ResearchPlan | None = None,
        iteration: int = 0,
        max_iterations: int = 2,
        research_id: str = "",
    ) -> tuple[list[Claim], list[Contradiction], list[ClaimSupportResult], SufficiencyResult]:
        """
        Returns updated claims, contradictions, per-claim reviews, and sufficiency.
        """
        with log_event("fact_checker", "fact_check", research_id=research_id):
            source_map = {s.source_id: s for s in sources}
            evidence_map = evidence_by_id or {}
            if evidence_list:
                for e in evidence_list:
                    evidence_map.setdefault(e.evidence_id, e.text)

            reviews: list[ClaimSupportResult] = []
            for claim in claims:
                review = self._verify_single(claim, source_map, evidence_map)
                claim.verification_status = review.status
                claim.confidence = review.confidence
                claim.verification_reason = review.reason
                reviews.append(review)

            contradictions = detect_contradictions(
                claims, llm=self.llm, prompt_template=self.prompt
            )
            # Mark conflicting claims from true contradictions
            conflicting_ids = {
                cid
                for ctr in contradictions
                if ctr.is_true_contradiction
                for cid in ctr.claim_ids
            }
            for claim in claims:
                if claim.claim_id in conflicting_ids:
                    claim.verification_status = VerificationStatus.CONFLICTING
                    for r in reviews:
                        if r.claim_id == claim.claim_id:
                            r.status = VerificationStatus.CONFLICTING
                            r.reason = (r.reason + " Marked conflicting with another claim.").strip()

            supported_n = sum(
                1
                for c in claims
                if c.verification_status
                in {VerificationStatus.SUPPORTED, VerificationStatus.PARTIALLY_SUPPORTED}
            )
            unsupported_n = sum(1 for c in claims if is_unsupported_status(c.verification_status))
            conflicting_n = sum(1 for c in claims if is_conflicting_status(c.verification_status))
            logger.info(
                "[FactChecker] %d supported | %d unsupported | %d conflicting",
                supported_n,
                unsupported_n,
                conflicting_n,
            )

            sufficiency = evaluate_sufficiency(
                claims=claims,
                sources=sources,
                contradictions=contradictions,
                plan=plan,
                iteration=iteration,
                max_iterations=max_iterations,
            )
            return claims, contradictions, reviews, sufficiency

    def _verify_single(
        self,
        claim: Claim,
        source_map: dict[str, Source],
        evidence_map: dict[str, str],
    ) -> ClaimSupportResult:
        if not claim.source_ids:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNSUPPORTED,
                confidence=0.1,
                reason="Claim has no linked source_ids.",
            )
        missing_sources = [sid for sid in claim.source_ids if sid not in source_map]
        if missing_sources:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNSUPPORTED,
                confidence=0.15,
                reason=f"Referenced sources missing from store: {missing_sources}",
            )
        if not claim.evidence_ids:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNSUPPORTED,
                confidence=0.2,
                reason="Claim has no evidence_ids.",
            )

        evidence_texts = []
        for eid in claim.evidence_ids:
            text = evidence_map.get(eid, "")
            if text:
                evidence_texts.append(text)
        if not evidence_texts:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNSUPPORTED,
                confidence=0.15,
                reason="No retrieved evidence text found for evidence_ids.",
            )

        # Evidence must appear in at least one linked source
        grounded = False
        for sid in claim.source_ids:
            src = source_map.get(sid)
            blob = ((src.content if src else "") + " " + (src.snippet if src else "")).lower()
            for et in evidence_texts:
                if et[:40].lower() in blob or et.lower() in blob:
                    grounded = True
                    break
            if grounded:
                break
        if not grounded:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNSUPPORTED,
                confidence=0.2,
                reason="Evidence span not found in linked source content.",
            )

        # Soft lexical overlap between claim and evidence
        claim_tokens = {
            t for t in re.findall(r"[a-z0-9]+", claim.claim.lower()) if len(t) > 2
        }
        ev_blob = " ".join(evidence_texts).lower()
        overlap = sum(1 for t in claim_tokens if t in ev_blob) if claim_tokens else 0
        overlap_ratio = overlap / max(1, len(claim_tokens))

        # Numeric consistency when structured value present
        if claim.value is not None:
            ev_norm = ev_blob.replace(",", "").replace(" ", "")
            raw = str(claim.value).replace(",", "").strip()
            # Accept both "25000" and "25000.0" forms
            candidates = {raw}
            try:
                num = float(raw)
                if num == int(num):
                    candidates.add(str(int(num)))
                candidates.add(f"{num:g}")
            except ValueError:
                pass
            if not any(c and c in ev_norm for c in candidates):
                return ClaimSupportResult(
                    claim_id=claim.claim_id,
                    status=VerificationStatus.UNSUPPORTED,
                    confidence=0.25,
                    reason="Numerical value in claim not present in evidence.",
                )

        if overlap_ratio >= 0.35:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.SUPPORTED,
                confidence=min(0.95, 0.6 + overlap_ratio * 0.3),
                reason="Evidence directly supports the stated claim.",
            )
        if overlap_ratio >= 0.2:
            return ClaimSupportResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.PARTIALLY_SUPPORTED,
                confidence=0.55,
                reason="Evidence partially overlaps the claim; interpret cautiously.",
            )
        return ClaimSupportResult(
            claim_id=claim.claim_id,
            status=VerificationStatus.UNSUPPORTED,
            confidence=0.3,
            reason="Evidence does not sufficiently support the claim wording.",
        )
