# Deployment (Render + Atlas + Groq)

## Stack

| Piece | Where |
|-------|--------|
| MongoDB | Atlas M0 (free) |
| AI (FastAPI + Groq) | Render web service `researchx-ai` (Python) |
| Express | Render web service `researchx-api` |
| React | Render static site `researchx-web` |

Blueprint: `render.yaml`. **Never put API keys in git** — paste them when Render prompts for `sync: false` values.

---

## Local Groq demo (paid models)

Your root `.env` / `apps/ai-service/.env` should have:

```
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
MOCK_MODE=false
GROQ_API_KEY=...
GROQ_API_KEY_2=...   # optional failover
GROQ_API_KEY_3=...
SEARCH_PROVIDER=tavily
```

```powershell
npm run dev
```

Open http://127.0.0.1:5173 → New research → leave **Mock mode** off → run a query. Progress + report use live Groq.

---

## Render Blueprint

1. Push this repo to GitHub  
2. Render → **New → Blueprint** → select the repo  
3. When prompted, paste from your local `.env` (do not commit these):

| Prompt | Value |
|--------|--------|
| `GROQ_API_KEY` (+ `_2`, `_3`) | your Groq keys |
| `TAVILY_API_KEY` / `SERPER_API_KEY` | search keys (or leave blank and set `SEARCH_PROVIDER=duckduckgo` in the dashboard) |
| `MONGODB_URI` | Atlas URI with DB `researchx` (**required** — API will crash without it) |
| `CORS_ORIGINS` | `https://researchx-web.onrender.com` (final web URL) |
| `CORS_ORIGIN` | same web URL |
| `VITE_API_URL` | `https://researchx-api.onrender.com` |

If the API logs say `MONGODB_URI: Required`, open **researchx-api → Environment**, paste your Atlas connection string, and redeploy.

`AI_SERVICE_TOKEN` and `JWT_SECRET` are auto-generated. Express gets the AI hostname via `fromService` and prefixes `https://` automatically.

4. After first deploy, confirm URLs, update CORS if needed, then **Clear build cache + deploy** on the web service so `VITE_API_URL` is baked into the SPA.

Defaults in the Blueprint: `MOCK_MODE=false`, `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-20b`.

---

## Atlas

Free M0 cluster → Network Access `0.0.0.0/0` → Database user → connection string with `/researchx`.

---

## Cold starts

Free Render services sleep after idle. First hit can take ~1 minute.
