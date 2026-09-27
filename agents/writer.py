"""Writer Agent — citation-grounded report from verified claims only."""

from __future__ import annotations

from evidence.citation import build_references, claims_with_citations, validate_citations
from prompts import load_prompt
from providers.llm.base import LLMProvider
from schemas.claim import (
    Claim,
    Contradiction,
    Evidence,
    VerificationStatus,
    is_conflicting_status,
    is_reportable_claim,
    is_unsupported_status,
)
from schemas.report import AnalysisResult, ResearchReport
from schemas.source import Source
from utils.helpers import safe_json_loads, truncate
from utils.logging import get_logger, log_event

logger = get_logger("researchx.agents.writer")


class WriterAgent:
    """Produce a Markdown + structured research report from verified evidence."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.prompt = load_prompt("writer")

    def write(
        self,
        *,
        research_id: str,
        query: str,
        claims: list[Claim],
        sources: list[Source],
        contradictions: list[Contradiction],
        analysis: list[AnalysisResult],
        evidence: list[Evidence] | None = None,
        limitations: list[str] | None = None,
        completed_with_limitations: bool = False,
    ) -> ResearchReport:
        with log_event("writer", "write_report", research_id=research_id):
            refs = build_references(sources)
            reportable = [c for c in claims if is_reportable_claim(c.verification_status)]
            conflicting = [c for c in claims if is_conflicting_status(c.verification_status)]
            unsupported = [c for c in claims if is_unsupported_status(c.verification_status)]

            # Writer must not invent — only receive verified/reportable + conflict context
            payload = {
                "query": query,
                "verified_claims": [c.model_dump() for c in reportable],
                "conflicting_claims": [c.model_dump() for c in conflicting],
                "sources": [{"source_id": s.source_id, "title": s.title, "url": s.url} for s in sources],
                "contradictions": [c.model_dump() for c in contradictions],
                "analysis": [a.model_dump() for a in analysis],
                "limitations": limitations or [],
                "unsupported_count": len(unsupported),
                "completed_with_limitations": completed_with_limitations,
            }
            user = (
                "TASK\nWrite a citation-grounded research report from the provided "
                "VERIFIED claims only. Do NOT invent facts. Do NOT present unsupported "
                "claims as established findings. Present conflicting evidence as disagreement.\n\n"
                f"UNTRUSTED RESEARCH DATA\n{truncate(str(payload), 20000)}\n\n"
                "REQUIRED OUTPUT\nJSON matching the writer schema."
            )
            try:
                raw = self.llm.complete(user, system=self.prompt, json_mode=True, temperature=0.2)
                data = safe_json_loads(raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Writer LLM failed (%s); using template report", exc)
                data = self._fallback(query, reportable, contradictions, completed_with_limitations)

            findings = list(data.get("key_findings") or [])
            if not any("[" in f for f in findings):
                findings = claims_with_citations(reportable[:10], reportable_only=False) or findings
            if not findings and completed_with_limitations:
                findings = ["INSUFFICIENT_EVIDENCE: Not enough verified claims to support firm findings."]

            lims = list(data.get("limitations") or limitations or [])
            if completed_with_limitations and not any("insufficient" in x.lower() for x in lims):
                lims.append(
                    "Research completed with limitations: some required evidence remained insufficient "
                    "after the maximum research iterations."
                )
            if unsupported:
                lims.append(
                    f"{len(unsupported)} claim(s) were marked unsupported and excluded from key findings."
                )

            conflict_summary = data.get("contradictions_summary") or (
                "; ".join(c.description for c in contradictions)
                if contradictions
                else (
                    "Conflicting claims were detected; see Conflicting Evidence."
                    if conflicting
                    else "No contradictions detected."
                )
            )

            status_note = (
                "COMPLETED_WITH_LIMITATIONS"
                if completed_with_limitations
                else ("INSUFFICIENT_EVIDENCE" if not reportable else "")
            )

            report = ResearchReport(
                research_id=research_id,
                title=data.get("title") or f"Research Report: {query}",
                query=query,
                executive_summary=data.get("executive_summary", ""),
                methodology=data.get("methodology", ""),
                key_findings=findings,
                detailed_analysis=data.get("detailed_analysis", ""),
                trends=list(data.get("trends") or []),
                contradictions_summary=conflict_summary,
                limitations=lims,
                conclusion=data.get("conclusion", ""),
                references=refs,
                charts=[a.chart for a in analysis if a.chart],
                chart_data=[a.chart_data for a in analysis if a.chart_data],
                tables=self._tables_from_analysis(analysis),
                status_note=status_note,
            )
            report.markdown = self._to_markdown(report, reportable, conflicting, analysis)
            bad = validate_citations(report.markdown, sources)
            if bad:
                logger.warning("Removing unknown citations: %s", bad)
                for sid in bad:
                    report.markdown = report.markdown.replace(f"[{sid}]", "")
            logger.info("[Writer] Report generated (%d verified claims cited)", len(reportable))
            return report

    def _fallback(
        self,
        query: str,
        claims: list[Claim],
        contradictions: list[Contradiction],
        completed_with_limitations: bool,
    ) -> dict:
        findings = claims_with_citations(claims[:10])
        return {
            "title": f"Research Report: {query}",
            "executive_summary": (
                f"This report summarizes verified evidence for: {query}. "
                f"{len(claims)} supported claim(s) were included."
                + (
                    " Some evidence gaps remain after the research iteration limit."
                    if completed_with_limitations
                    else ""
                )
            ),
            "methodology": (
                "The ResearchX pipeline planned subtasks, searched the web, extracted evidence, "
                "fact-checked claims against source passages, ran quantitative analysis on structured "
                "data, and drafted this citation-grounded report. Unsupported claims were excluded."
            ),
            "key_findings": findings
            or ["INSUFFICIENT_EVIDENCE: No verified claims available."],
            "detailed_analysis": "See key findings and analysis JSON for structured details.",
            "trends": [],
            "contradictions_summary": (
                "; ".join(c.description for c in contradictions)
                if contradictions
                else "No contradictions detected."
            ),
            "limitations": [
                "Evidence coverage depends on search provider results and page accessibility.",
                "Source quality scores are prioritization heuristics, not truth labels.",
            ],
            "conclusion": "Findings should be interpreted with attention to contradictions and data gaps.",
        }

    @staticmethod
    def _tables_from_analysis(analysis: list[AnalysisResult]) -> list[dict]:
        tables = []
        for a in analysis:
            if a.values:
                tables.append({"title": a.metric, "rows": a.values})
        return tables

    def _to_markdown(
        self,
        report: ResearchReport,
        reportable: list[Claim],
        conflicting: list[Claim],
        analysis: list[AnalysisResult],
    ) -> str:
        lines: list[str] = [
            f"# {report.title}",
            "",
            f"**Research ID:** {report.research_id}",
            f"**Question:** {report.query}",
        ]
        if report.status_note:
            lines += ["", f"**Status:** {report.status_note}"]
        lines += [
            "",
            "## Executive Summary",
            report.executive_summary,
            "",
            "## Research Question",
            report.query,
            "",
            "## Scope & Methodology",
            report.methodology,
            "",
            "## Key Findings",
        ]
        for f in report.key_findings:
            lines.append(f"- {f}")
        lines += ["", "## Detailed Analysis", report.detailed_analysis, ""]

        if report.tables:
            lines.append("## Tables")
            for table in report.tables:
                lines.append(f"### {table.get('title', 'Table')}")
                rows = table.get("rows") or []
                if rows and isinstance(rows[0], dict):
                    headers = list(rows[0].keys())
                    lines.append("| " + " | ".join(headers) + " |")
                    lines.append("| " + " | ".join("---" for _ in headers) + " |")
                    for row in rows:
                        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
                lines.append("")

        if report.trends:
            lines.append("## Trends")
            for t in report.trends:
                lines.append(f"- {t}")
            lines.append("")

        if analysis:
            lines.append("## Quantitative Analysis")
            for a in analysis:
                if getattr(a, "status", "ok") == "skipped":
                    continue
                lines.append(f"### {a.metric} ({a.calculation or a.analysis_type})")
                if a.formula:
                    lines.append(f"_Formula:_ `{a.formula}`")
                if a.result is not None:
                    lines.append(f"_Calculated result:_ `{a.result}`")
                if a.source_ids:
                    cites = "".join(f"[{sid}]" for sid in a.source_ids)
                    lines.append(f"_Source inputs:_ {cites}")
                if a.interpretation:
                    lines.append(a.interpretation)
                lines.append("")

        lines += ["## Conflicting Evidence", report.contradictions_summary or "None detected.", ""]
        if conflicting:
            for c in conflicting:
                cites = "".join(f"[{sid}]" for sid in c.source_ids)
                lines.append(f"- {c.claim} {cites} _(status: {c.verification_status.value})_")
            lines.append("")

        lines.append("## Limitations")
        for lim in report.limitations:
            lines.append(f"- {lim}")
        lines += ["", "## Conclusion", report.conclusion, "", "## References"]
        for ref in report.references:
            lines.append(ref.get("citation") or f"[{ref.get('id')}] {ref.get('url')}")
        lines.append("")
        return "\n".join(lines)
