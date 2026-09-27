# Docker

## Images

| Dockerfile | Image role |
|------------|------------|
| `infrastructure/docker/Dockerfile.web` | Multi-stage Vite build → nginx static |
| `infrastructure/docker/Dockerfile.server` | Multi-stage Express build → Node runtime |
| `infrastructure/docker/Dockerfile.ai-service` | Python slim + uvicorn |

All images:

- Avoid baking secrets (use Compose/` .env`)
- Expose health checks
- Prefer non-root users where practical

## Compose stack

`docker-compose.yml` at repo root:

```text
web → server → ai-service
         ↘ mongodb
ai-service / server → redis (optional cache)
```

```bash
docker compose up --build
docker compose ps
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5000/ready
docker compose down
```

## Notes

- `MOCK_MODE=true` by default in Compose so the stack runs without paid LLM keys.
- Mount `./data` into the AI service for cache/chroma/outputs.
- Redis uses no persistence (`--save ""`) — it is a cache, not durable storage.
- **Documents:** both `server` and `ai-service` mount `./data/documents` at `/data/documents` and set `DOCUMENTS_PATH=/data/documents`. This keeps Express `absolutePath` values readable by FastAPI RAG.
- Production may run the same images without Compose (and without Redis).
