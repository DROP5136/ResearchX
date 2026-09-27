# Deployment

See the free-first guide: **[docs/deployment.md](../deployment.md)**.

Quick local stack:

```bash
docker compose up --build
```

Do not expose MongoDB, Redis, or FastAPI publicly. Express + static web only.
