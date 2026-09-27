# Testing

## Commands

```powershell
# Python AI service (+ FastAPI integration)
cd apps\ai-service
..\..\.venv\Scripts\python.exe -m pytest -q

# Express (includes e2e.smoke.test.ts — primary product regression)
npm run test -w researchx-server
npm run lint -w researchx-server

# Web
npm run test -w researchx-web
npm run lint -w researchx-web
npm run build -w researchx-web

# Evaluation / performance (mock)
cd apps\ai-service
..\..\.venv\Scripts\python.exe -m app.evaluation.run --mock
```

## Primary smoke test

`apps/server/tests/e2e.smoke.test.ts` covers:

register/login → project → research job (202) → status progress → completed report
(sources, claims, evidence, analysis, charts) → ownership isolation

FastAPI is mocked; Python suite covers LangGraph mock end-to-end in `tests/integration/test_api.py`.

## Coverage map

| Area | Tests |
|------|--------|
| Redis optional | `test_redis_optional.py`, `jobs.test.ts` |
| Job lifecycle / cancel | `test_job_lifecycle.py`, `test_cancel_job.py`, `jobs.test.ts` |
| SSE progress | `jobs.test.ts` |
| Auth / ownership | `security.test.ts`, `e2e.smoke.test.ts` |
| PDF RAG | `test_document_rag.py`, `test_documents_api.py` |
| Quantitative | `test_quantitative.py`, `test_analysis.py` |
| Mock full research | `test_api.py`, `e2e.smoke.test.ts` |

## Docker Compose smoke

Requires Docker Desktop running:

```powershell
docker compose up --build -d
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5000/ready
# open http://127.0.0.1:5173 — register, start mock research
docker compose down
```

**Document paths:** Express and AI service both use absolute `DOCUMENTS_PATH=/data/documents` with the same volume mount so PDF RAG works in Compose.
