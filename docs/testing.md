# Testing

```powershell
# Python
cd apps\ai-service
..\..\.venv\Scripts\python.exe -m pytest -q

# Express
npm run test -w researchx-server
npm run lint -w researchx-server

# Web
npm run test -w researchx-web
npm run lint -w researchx-web
npm run build -w researchx-web

# Evaluation (mock)
cd apps\ai-service
..\..\.venv\Scripts\python.exe -m app.evaluation.run --mock
```

## Smoke test

`apps/server/tests/e2e.smoke.test.ts` covers register → project → research job → progress → report (FastAPI mocked).

LangGraph mock flow: `apps/ai-service/tests/integration/test_api.py`.

## Useful test files

| Area | Location |
|------|----------|
| Redis optional | `test_redis_optional.py`, `jobs.test.ts` |
| Jobs / cancel / SSE | `test_job_lifecycle.py`, `test_cancel_job.py`, `jobs.test.ts` |
| Auth / ownership | `security.test.ts` |
| PDF RAG | `test_document_rag.py`, `test_documents_api.py` |
| Numbers | `test_quantitative.py` |

## Docker smoke

```powershell
docker compose up --build -d
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:8000/health
docker compose down
```

In Compose, Express and AI both use `DOCUMENTS_PATH=/data/documents` on the same volume.
