"""Evidence Extraction Agent — claims from sources (evidence-grounded only)."""

from __future__ import annotations

from app.evidence.claim import make_claim, make_evidence
from app.prompts import load_prompt
from app.providers.llm.base import LLMProvider
from app.schemas.claim import Claim, Evidence
from app.schemas.source import Source
from app.utils.helpers import safe_json_loads, truncate
from app.utils.logging import get_logger, log_event

logger = get_logger("researchx.agents.extractor")


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def evidence_supported_by_source(evidence_text: str, content: str) -> bool:
    """Require evidence to be a near-verbatim span from the source content."""
    if not evidence_text or not content:
        return False
    ev = _normalize(evidence_text)
    blob = _normalize(content)
    if ev in blob:
        return True
    # Allow short fuzzy match: first ~60 chars of evidence appear in source
    probe = ev[:60] if len(ev) > 60 else ev
    return len(probe) >= 20 and probe in blob


class ExtractorAgent:
    """Extract structured claims grounded in source evidence."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.system_prompt = load_prompt("extractor")

    def extract_from_sources(
        self,
        sources: list[Source],
        research_question: str,
        research_id: str = "",
    ) -> tuple[list[Claim], list[Evidence]]:
        with log_event("extractor", "extract_claims", research_id=research_id):
            claims: list[Claim] = []
            evidence: list[Evidence] = []
            for source in sources:
                c, e = self.extract_from_source(source, research_question)
                claims.extend(c)
                evidence.extend(e)
            logger.info(
                "[Extraction] %d claims extracted from %d sources",
                len(claims),
                len(sources),
            )
            return claims, evidence

    def extract_from_source(
        self,
        source: Source,
        research_question: str,
    ) -> tuple[list[Claim], list[Evidence]]:
        content = source.content or source.snippet or ""
        if not content.strip():
            return [], []

        user = (
            "TASK\nExtract structured factual claims from the source.\n\n"
            f"Research context: {research_question}\n"
            f"source_id: {source.source_id}\n"
            f"url: {source.url}\n"
            f"title: {source.title}\n\n"
            "UNTRUSTED SOURCE CONTENT\n"
            "---------- BEGIN UNTRUSTED DATA ----------\n"
            f"{truncate(content, 8000)}\n"
            "---------- END UNTRUSTED DATA ----------\n\n"
            "REQUIRED OUTPUT\nJSON with claims array. Evidence MUST be a verbatim span "
            "copied from the source. Do NOT invent numbers or facts not present in the text."
        )
        try:
            raw = self.llm.complete(user, system=self.system_prompt, json_mode=True, temperature=0.1)
            data = safe_json_loads(raw)
            items = data.get("claims", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Extraction failed for %s: %s", source.source_id, exc)
            return [], []

        claims: list[Claim] = []
        evidence_list: list[Evidence] = []
        page = None
        document_id = None
        chunk_id = None
        if source.metadata:
            page = source.metadata.get("page")
            document_id = source.metadata.get("document_id")
            chunk_id = source.metadata.get("chunk_id")

        for item in items[:8]:
            try:
                evidence_text = str(item.get("evidence") or "").strip()
                claim_text = str(item.get("claim") or "").strip()
                if not claim_text:
                    continue
                if not evidence_text:
                    # Do not invent evidence from the claim wording alone
                    logger.debug("Rejecting claim without evidence span: %s", claim_text[:80])
                    continue
                if not evidence_supported_by_source(evidence_text, content):
                    logger.debug(
                        "Rejecting unsupported claim (evidence not in source %s): %s",
                        source.source_id,
                        claim_text[:80],
                    )
                    continue

                conf = float(item.get("confidence", 0.7))
                start = content.lower().find(evidence_text[:40].lower())
                end = start + len(evidence_text) if start >= 0 else None
                start_offset = start if start >= 0 else None

                ev = make_evidence(
                    source.source_id,
                    evidence_text,
                    page=page if isinstance(page, int) else None,
                    start_offset=start_offset,
                    end_offset=end,
                    chunk_id=chunk_id,
                    document_id=document_id,
                )
                evidence_list.append(ev)
                claim = make_claim(
                    claim_text,
                    source_ids=[source.source_id],
                    evidence_ids=[ev.evidence_id],
                    entity=item.get("entity"),
                    metric=item.get("metric"),
                    value=item.get("value"),
                    unit=item.get("unit"),
                    period=item.get("period"),
                    confidence=max(0.0, min(1.0, conf)),
                )
                claims.append(claim)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping malformed claim: %s", exc)
        return claims, evidence_list
