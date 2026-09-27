# Deployment

ResearchX deploys as three services + MongoDB. Redis is optional (leave empty).

**Recommended free stack:** MongoDB Atlas (M0) + Render (AI + API + static web).

Keep MongoDB private credentials in the platform dashboard. Protect FastAPI with `AI_SERVICE_TOKEN` (Express is the public API).

---

## 1. Push to GitHub

Commit and push `researchx-ai` to a GitHub repo.

---

## 2. MongoDB Atlas (free)

1. Create an M0 cluster
2. Database user + password
3. Network Access → `0.0.0.0/0`
4. Copy connection string → use database name `researchx`

Example:

```text
mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/researchx?retryWrites=true&w=majority
```

---

## 3. Deploy with Render Blueprint

1. Open [Render](https://dashboard.render.com) → **New** → **Blueprint**
2. Connect the GitHub repo (file `render.yaml` at repo root)
3. Create the blueprint
4. In the dashboard, set these **secret / sync:false** values:

### researchx-ai

| Key | Value |
|-----|--------|
| `AI_SERVICE_TOKEN` | long random shared secret |
| `CORS_ORIGINS` | `https://researchx-web.onrender.com` (your static URL after it exists) |

### researchx-api

| Key | Value |
|-----|--------|
| `MONGODB_URI` | Atlas URI |
| `JWT_SECRET` | ≥24 random characters |
| `AI_SERVICE_TOKEN` | **same** as AI service |
| `FASTAPI_URL` | `https://researchx-ai.onrender.com` (no trailing slash) |
| `CORS_ORIGIN` | `https://researchx-web.onrender.com` |

### researchx-web

| Key | Value |
|-----|--------|
| `VITE_API_URL` | `https://researchx-api.onrender.com` |

5. Redeploy **web** after `VITE_API_URL` is set (it is baked into the JS bundle).
6. Redeploy **api** / **ai** after CORS URLs match the final web hostname.

### Manual create (if not using Blueprint)

| Service | Type | Build | Start / publish |
|---------|------|-------|-----------------|
| AI | Web / Python | `pip install -r requirements.txt` (root `apps/ai-service`) | `python -m app.api.run_prod` |
| API | Web / Node | `npm install && npm run build -w researchx-server` | `npm start -w researchx-server` |
| Web | Static | `npm install && npm run build -w researchx-web` | publish `apps/web/dist` + SPA rewrite `/* → /index.html` |

---

## 4. Verify

```text
https://researchx-ai.onrender.com/health
https://researchx-api.onrender.com/health
https://researchx-api.onrender.com/ready
https://researchx-web.onrender.com
```

Then: register → project → research (mock mode) → report.

First hit after idle can take 30–60s (free instances sleep).

---

## Environment reference

**Express (`researchx-api`)**

- `NODE_ENV=production`
- `HOST=0.0.0.0`
- `MONGODB_URI`, `JWT_SECRET`, `FASTAPI_URL`, `AI_SERVICE_TOKEN`, `CORS_ORIGIN`
- `ALLOW_MOCK_MODE=true` for demos without paid LLMs
- `REDIS_URL=` (empty)
- `DOCUMENTS_PATH=./data/documents` (ephemeral on free tier)

**AI (`researchx-ai`)**

- `APP_ENV=production`
- `AI_SERVICE_TOKEN` (must match Express)
- `MOCK_MODE=true`, `LLM_PROVIDER=mock`, `SEARCH_PROVIDER=duckduckgo`
- Or live: `MOCK_MODE=false`, `LLM_PROVIDER=groq`, `GROQ_API_KEY=...`
- Keep `MAX_*` low on free RAM

**Web**

- `VITE_API_URL` = public Express URL (build-time only)

---

## Local production-like check

```powershell
cd "c:\GENAI PROJECT\researchx-ai"
$env:NODE_ENV="production"
$env:AI_SERVICE_TOKEN="test-token-change-me-now"
$env:JWT_SECRET="local-prod-secret-at-least-24c"
$env:MONGODB_URI="mongodb://127.0.0.1:27017/researchx"
$env:FASTAPI_URL="http://127.0.0.1:8000"
$env:CORS_ORIGIN="http://127.0.0.1:4173"
npm run build
npm start -w researchx-server
```

AI:

```powershell
cd apps\ai-service
$env:APP_ENV="production"
$env:AI_SERVICE_TOKEN="test-token-change-me-now"
$env:MOCK_MODE="true"
..\..\.venv\Scripts\python.exe -m app.api.run_prod
```

---

## Limits on free hosting

- Services sleep after idle → cold starts
- No persistent disk → uploaded PDFs may disappear after restart
- ~512MB RAM → keep concurrency limits low; prefer mock mode for demos
- Atlas free tier storage/connection limits apply

Redis is not required. Do not enable Kafka or Kubernetes.
