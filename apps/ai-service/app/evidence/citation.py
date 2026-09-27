"""Citation tracking helpers."""

from __future__ import annotations

import re

from app.schemas.claim import Claim, Evidence, is_reportable_claim
from app.schemas.source import Source


def citation_tag(source_id: str) -> str:
    return f"[{source_id}]"


def build_references(sources: list[Source]) -> list[dict[str, str]]:
    refs = []
    for s in sorted(sources, key=lambda x: x.source_id):
        refs.append(
            {
                "id": s.source_id,
                "title": s.title or s.domain or s.source_id,
                "url": s.url,
                "citation": f"[{s.source_id}] {s.title or s.domain} — {s.url}",
            }
        )
    return refs


def validate_citations(text: str, sources: list[Source]) -> list[str]:
    """Return citation IDs in text that do not exist in the source DB."""
    known = {s.source_id for s in sources}
    used = set(re.findall(r"\[(SRC_[a-zA-Z0-9]+)\]", text))
    return sorted(used - known)


def validate_claim_traceability(
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
) -> list[str]:
    """Return claim IDs that break the Claim → Evidence → Source chain."""
    known_sources = {s.source_id for s in sources}
    known_evidence = {e.evidence_id: e for e in evidence}
    broken: list[str] = []
    for c in claims:
        if not c.source_ids or any(sid not in known_sources for sid in c.source_ids):
            broken.append(c.claim_id)
            continue
        if not c.evidence_ids:
            broken.append(c.claim_id)
            continue
        for eid in c.evidence_ids:
            ev = known_evidence.get(eid)
            if ev is None or ev.source_id not in c.source_ids:
                broken.append(c.claim_id)
                break
    return broken


def claims_with_citations(claims: list[Claim], *, reportable_only: bool = False) -> list[str]:
    lines = []
    for c in claims:
        if reportable_only and not is_reportable_claim(c.verification_status):
            continue
        cites = "".join(citation_tag(sid) for sid in c.source_ids)
        lines.append(f"{c.claim} {cites}".strip())
    return lines
