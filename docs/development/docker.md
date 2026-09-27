# Docker

## Images

| Dockerfile | Role |
|------------|------|
| `infrastructure/docker/Dockerfile.web` | Vite build → nginx |
| `infrastructure/docker/Dockerfile.server` | Express build → Node |
| `infrastructure/docker/Dockerfile.ai-service` | Python + uvicorn |

Secrets stay in `.env` / Compose env, not in Dockerfiles.

## Compose

```bash
docker compose up --build
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:8000/health
docker compose down
```

Notes:

- Default `MOCK_MODE=true` so the stack runs without paid API keys
- `./data` is mounted for cache / chroma / outputs
- Express and AI both mount `./data/documents` at `/data/documents`
- Redis is cache-only (no persistence)
