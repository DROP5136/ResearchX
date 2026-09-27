# ResearchX

Multi-agent AI research platform: React client → Express/Mongo app server → FastAPI/LangGraph AI service.

## Overview

ResearchX turns a research question into a sourced, fact-checked, analyzed report. The monorepo separates three apps so each can scale and deploy independently while sharing API contracts.

## Architecture

```text
React (apps/web)
    ↓  HTTP / JWT
Express + MongoDB (apps/server)
    ↓  HTTP
FastAPI (apps/ai-service)
    ↓
LangGraph workflow
    ↓
Research → Evidence → Fact Checking → Analysis → Report
    ↓
MongoDB (app data)  |  Local storage / Chroma (AI artifacts)
```

Dependency direction: **web → server → ai-service**. The web client never imports Python. The Node server never imports Python modules.

## Repository Structure

```text
researchx-ai/
├── apps/
│   ├── ai-service/     # Python LangGraph + FastAPI
│   ├── server/         # Express + MongoDB
│   └── web/            # React + Vite
├── packages/
│   ├── contracts/      # Shared TS API types
│   └── config/         # Shared config docs
├── infrastructure/     # Docker, nginx, helper scripts
├── docs/               # Architecture & development docs
├── evaluation/         # Benchmarks + results (artifacts)
├── data/               # Runtime cache / chroma / outputs
├── docker-compose.yml
├── Makefile
├── package.json        # npm workspaces (server, web, packages)
├── PRD.md
└── README.md
```

## Tech Stack

| Layer | Stack |
|-------|--------|
| Web | React 18, TypeScript, Vite, Tailwind |
| Server | Node.js, Express, Mongoose, JWT |
| AI | Python 3.11+, FastAPI, LangGraph, Groq/Gemini, Chroma |
| Data | MongoDB (users/projects/sessions), local files (reports/cache) |

## Local Development

### Prerequisites

- Python 3.11+ with venv at repo root `.venv/`
- Node.js 18+
- MongoDB (Atlas URI or local `mongodb://127.0.0.1:27017/researchx`)

### Install

```powershell
# Python deps
.\.venv\Scripts\Activate.ps1
pip install -r apps/ai-service/requirements.txt

# Node workspaces (server + web + contracts)
npm install
```

### Environment

Copy examples (never commit real `.env` files):

```powershell
copy apps\ai-service\.env.example apps\ai-service\.env
copy apps\server\.env.example apps\server\.env
copy apps\web\.env.example apps\web\.env
```

See [Environment Variables](#environment-variables) below.

## Running AI Service

```powershell
cd apps\ai-service
..\..\.venv\Scripts\Activate.ps1
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

Health: http://127.0.0.1:8000/health  
Docs: http://127.0.0.1:8000/docs

CLI (optional):

```powershell
cd apps\ai-service
python -m app.main "Your research question" --mock
```

## Running Backend

```powershell
npm run dev -w researchx-server
```

Health: http://127.0.0.1:5000/health

## Running Frontend

```powershell
npm run dev -w researchx-web
```

Open: http://127.0.0.1:5173

## Running Tests

```powershell
# Python
cd apps\ai-service
..\..\.venv\Scripts\python.exe -m pytest -q

# Node + web
npm run test -w researchx-server
npm run test -w researchx-web
```

Or: `make test` (Windows: run the Make targets manually / use Git Bash).

## Environment Variables

| App | File | Notes |
|-----|------|--------|
| AI | `apps/ai-service/.env` | LLM/search keys, paths, mock mode |
| Server | `apps/server/.env` | `MONGODB_URI`, `JWT_SECRET`, `FASTAPI_URL` |
| Web | `apps/web/.env` | Only `VITE_API_URL` (public) |

Root `.env.example` mirrors AI service vars for convenience.

## Docker

```powershell
docker compose up --build
```

Services: `web`, `server`, `ai-service`, `mongodb`. Dockerfiles live under `infrastructure/docker/`.

## Evaluation

Engine code: `apps/ai-service/app/evaluation/`  
Artifacts: `evaluation/benchmarks/`, `evaluation/results/`

```powershell
cd apps\ai-service
python -m app.evaluation.run --mock
```

## Deployment

See `docs/deployment/README.md`. Typical production layout: separate containers for web (nginx), server, ai-service, and managed MongoDB.

## Documentation

- [Architecture overview](docs/architecture/overview.md)
- [AI pipeline](docs/architecture/ai-pipeline.md)
- [Document / PDF RAG](docs/architecture/document-rag.md)
- [System flow](docs/architecture/system-flow.md)
- [API](docs/api/README.md)
- [Setup](docs/development/setup.md)
- [Testing](docs/development/testing.md)
- [PRD](PRD.md)

## Document research (PDF RAG)

1. Open **Documents**, pick a project, upload PDFs.
2. Wait until status is **Ready** (parsing → embedding → indexing).
3. Start **Research**, enable **Uploaded documents**, select files (and optionally Web).
4. In results, the **Sources** tab separates web vs document citations (page + excerpt).
