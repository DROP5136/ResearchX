# System flow

```text
Browser
  → POST /api/v1/auth/login          (Express)
  → POST /api/v1/projects            (Express → MongoDB)
  → POST /api/v1/research            (Express → FastAPI /api/v1/research)
  → GET  /api/v1/research/:id/status (Express polls FastAPI, updates Mongo session)
  → GET  /api/v1/research/:id        (Express merges FastAPI result + Mongo metadata)
```

AI service remains stateless from the browser’s perspective; the Express layer owns multi-user persistence.
