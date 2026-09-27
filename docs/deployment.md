# Deployment

ResearchX is designed to stay **free to build, run, and deploy**. Docker is for local reproducibility and portable images — it is **not** required in production. Redis is **optional**.

> Do not expose MongoDB, Redis, or the FastAPI AI service publicly. Only the static web app and the Express API should face the internet.

---

## Local development

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# edit JWT_SECRET; leave MOCK_MODE=true for free demo
docker compose up --build
```

| Service     | URL                         |
|-------------|-----------------------------|
| Web         | http://127.0.0.1:5173       |
| Express     | http://127.0.0.1:5000/health |
| FastAPI     | http://127.0.0.1:8000/health |
| MongoDB     | localhost:27017 (internal)  |
| Redis       | localhost:6379 (optional)   |

Cleanup:

```bash
docker compose down
# remove volumes too:
docker compose down -v
```

### Option B — Native processes

1. Start MongoDB locally (or free Atlas M0 URI).
2. Optionally start Redis (`redis-server`) or leave `REDIS_URL` empty.
3. Run AI service, Express, and Vite as documented in the root README.

---

## Free public deployment

Hosting providers change free tiers frequently. Prefer any combination that offers:

| Layer        | What to deploy                         | Notes |
|--------------|----------------------------------------|--------|
| Frontend     | Static build of `apps/web`             | Netlify / Cloudflare Pages / GitHub Pages / similar free static hosts |
| Express      | Node container or Node build           | Free PaaS (Render / Railway / Fly.io free allowances / similar) |
| FastAPI      | Python container or uvicorn process    | Same class of free PaaS; can share a host with Express if needed |
| MongoDB      | Free cluster (e.g. Atlas M0)           | Or a free Mongo-compatible tier |
| Redis        | Optional free Redis-compatible tier    | Or disable (`REDIS_URL` empty) |

### Build commands

```bash
# Frontend
cd apps/web && npm ci && npm run build
# Serve dist/ with any static host. Set VITE_API_URL to public Express URL at build time.

# Express
cd apps/server && npm ci && npm run build && npm start

# AI service
cd apps/ai-service
pip install -r requirements.txt
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

### Environment variables (production)

**Express**

- `MONGODB_URI` — free Mongo URI  
- `JWT_SECRET` — long random secret  
- `FASTAPI_URL` — private/internal URL of AI service  
- `AI_SERVICE_TOKEN` — shared secret (required when `NODE_ENV=production`)  
- `CORS_ORIGIN` — public frontend origin(s), comma-separated  
- `REDIS_URL` — optional  
- `ALLOW_MOCK_MODE=false` unless demoing without LLM keys  
- `DOCUMENTS_PATH` — persistent volume path for uploads  

**AI service**

- `AI_SERVICE_TOKEN` — same as Express  
- `LLM_PROVIDER` — `ollama` / `groq` / `gemini` / `mock`  
- `SEARCH_PROVIDER` — `duckduckgo` (free) or optional paid  
- `CORS_ORIGINS` — usually only Express origin if browser never hits FastAPI  
- `REDIS_URL` — optional  
- Cost controls: `MAX_SOURCES`, `MAX_RESEARCH_ITERATIONS`, `MAX_CONCURRENT_RESEARCH`, etc.  

**Web**

- `VITE_API_URL` — public Express base URL (baked in at build time)

### CORS / API URLs

1. Build web with `VITE_API_URL=https://your-express.example`.
2. Set Express `CORS_ORIGIN` to `https://your-frontend.example`.
3. Point Express `FASTAPI_URL` at the AI service **private** URL.
4. Do not put FastAPI or Mongo/Redis hostnames in the browser.

### Health checks

- Express: `GET /health` (liveness), `GET /ready` (Mongo required; Redis optional)
- AI: `GET /health` (liveness), `GET /ready` (data dirs; Redis optional)

### Free-tier limitations (expect these)

- Cold starts / sleeping services after idle
- Low CPU/RAM — keep `MAX_*` limits conservative; prefer `MOCK_MODE` for demos
- Ephemeral disks — mount persistent storage for `data/documents`, `data/outputs`, `data/chroma`
- Rate limits on free LLM/search APIs — fail gracefully; DuckDuckGo + mock remain viable

### Verify public deployment checklist

- [ ] Frontend builds and loads
- [ ] Frontend `VITE_API_URL` points at Express
- [ ] Express deployed and `/health` returns ok
- [ ] FastAPI deployed and `/health` returns ok (private)
- [ ] MongoDB connected (`/ready` on Express)
- [ ] Redis connected **or** deliberately disabled
- [ ] CORS allows frontend origin
- [ ] Environment variables set (no secrets in repo)
- [ ] Auth register/login works
- [ ] Mock or live research completes with progress
- [ ] PDF upload works (if volume mounted)
- [ ] Final report persists and reloads

---

## What this project deliberately does NOT require

- Kubernetes
- Kafka
- Paid cloud accounts as a hard dependency
- Paid database / Redis / monitoring as a hard dependency

Docker images remain portable if you later move to any container host.
