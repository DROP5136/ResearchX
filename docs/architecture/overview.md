# Architecture overview

ResearchX is a three-app monorepo:

1. **apps/web** — React SPA for auth, projects, research UX, evaluation dashboard.
2. **apps/server** — Express API for users, projects, sessions, JWT auth; proxies AI work to FastAPI.
3. **apps/ai-service** — FastAPI + LangGraph research pipeline (plan → research → extract → fact-check → analyze → write).

Shared TypeScript DTOs live in `packages/contracts`. Python schemas stay inside the AI service.
