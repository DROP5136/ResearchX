# ResearchX — Product Requirements

Scope for the Python multi-agent research engine and related app services.

## Pipeline

Planner → Research → Evidence → Fact Check → Analyst → Writer

## Requirements

- Provider abstractions for LLM and search (including mock mode)
- Citation-grounded reports stored locally (JSON) and via the app API
- PDF RAG and hybrid web + document research
- Claim grounding: Claim → Evidence → Source → URL
- Verification statuses: supported / partially_supported / conflicting / unsupported
- Evidence sufficiency checks and follow-up research within max iterations
- Deterministic quantitative analysis (YoY, CAGR, market share, rankings) without LLM arithmetic
- Chart-ready JSON for the frontend
- Pytest coverage and evaluation benchmarks
- Express/React app for auth, projects, jobs, and report UI

See `README.md` for setup and usage.
