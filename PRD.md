# ResearchX Product Requirements (Python Engine Scope)

This document captures the product specification used to implement the
`researchx-ai` Python multi-agent research engine.

## Phase 1 (complete)
- Multi-agent pipeline: Planner → Research → Extract → Fact Check → Analyst → Writer
- Free/open LLM + search provider abstractions
- Citation-grounded reports with local JSON storage
- PDF RAG + hybrid research
- Mock mode, pytest suite, and evaluation benchmarks
- CLI-first delivery; no React/Node backend in this phase

## Phase 2 (complete)
- Strict Claim → Evidence → Source → URL grounding (invented claims rejected)
- Verification statuses: supported / partially_supported / conflicting / unsupported
- Structured ClaimSupportResult reviews
- Evidence sufficiency decision + follow-up research tasks
- Max-iteration termination with COMPLETED_WITH_LIMITATIONS
- `evidence.json` in run outputs
- Writer excludes unsupported claims; surfaces conflicting evidence
- Observability logs: `[Planner]`, `[Research]`, `[Extraction]`, `[FactChecker]`, `[ResearchLoop]`, `[Analyst]`, `[Writer]`

## Phase 3 — Quantitative analysis (complete)
- DataPoint / Dataset / ChartData schemas with source/evidence traceability
- Claim → DataPoint extraction + unit normalization (million/billion/%)
- Deterministic Pandas engine: YoY, CAGR, market share, rankings, comparisons
- Chart-ready JSON (line / bar / grouped_bar / pie / area)
- Data-quality flags (duplicate, conflicting, outliers, div-by-zero)
- Analyst skips non-numerical questions
- CLI: `python main.py --demo-quant` and `--show-analysis`
- Outputs: `datapoints.json`, `dataset.json`, enriched `analysis.json`

See `README.md` for architecture, setup, and usage.


