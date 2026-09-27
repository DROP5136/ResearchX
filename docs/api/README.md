# ResearchX Express API

Application/business backend for ResearchX. AI execution stays in FastAPI (`FASTAPI_URL`).

Base URL (local): `http://127.0.0.1:5000`

Auth header for protected routes:

```http
Authorization: Bearer <jwt>
```

## Documents (PDF)

### POST `/api/v1/projects/:projectId/documents`

Multipart form field: `files` (one or more PDFs).

Returns `202` with `{ documentId, status: "processing", items: [...] }`.

### GET `/api/v1/projects/:projectId/documents`

List project documents (metadata only).

### GET `/api/v1/documents/:id/status`

Processing status (`uploaded` | `processing` | `ready` | `failed`) and stage.

### POST `/api/v1/documents/:id/retry`

### DELETE `/api/v1/documents/:id`

### Research with documents

`POST /api/v1/research` accepts `documentIds[]`, `enableDocumentResearch` / `enablePdfRag`, and `enableWebSearch`.

---

Error envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request"
  }
}
```

---

## Authentication

### POST `/api/v1/auth/register`

Auth: none

Request:

```json
{
  "name": "Lakshya",
  "email": "lakshya@example.com",
  "password": "password123"
}
```

Response `201`:

```json
{
  "token": "<jwt>",
  "user": {
    "id": "...",
    "name": "Lakshya",
    "email": "lakshya@example.com"
  }
}
```

Errors: `VALIDATION_ERROR`, `EMAIL_EXISTS`

### POST `/api/v1/auth/login`

Auth: none

Request:

```json
{
  "email": "lakshya@example.com",
  "password": "password123"
}
```

Response `200`: `{ "token": "...", "user": { ... } }`

Errors: `VALIDATION_ERROR`, `INVALID_CREDENTIALS`

### GET `/api/v1/auth/me`

Auth: required

Response `200`: `{ "user": { ... } }`

Errors: `UNAUTHORIZED`

---

## Projects

All routes require auth. Users only see their own projects.

### POST `/api/v1/projects`

```json
{ "name": "EV Study", "description": "India EV market" }
```

Response `201`: `{ "project": { "id", "name", "description", ... } }`

### GET `/api/v1/projects`

Response: `{ "items": [...], "total": N }`

### GET `/api/v1/projects/:id`

### PATCH `/api/v1/projects/:id`

```json
{ "name": "Updated name" }
```

### DELETE `/api/v1/projects/:id`

Errors: `PROJECT_NOT_FOUND`, `VALIDATION_ERROR`, `UNAUTHORIZED`

---

## Research

Express creates a Mongo `ResearchSession`, calls FastAPI `POST /api/v1/research`, stores `fastApiResearchId`, and syncs status/results on poll.

### POST `/api/v1/research`

Auth: required

```json
{
  "projectId": "<mongoObjectId>",
  "query": "Analyze the Indian EV market from 2022 to 2026",
  "depth": "quick",
  "mockMode": true
}
```

Response `202`:

```json
{
  "research": {
    "id": "<mongoId>",
    "projectId": "...",
    "query": "...",
    "status": "started",
    "fastApiResearchId": "RES_...",
    "progress": 0
  }
}
```

### GET `/api/v1/research/:id/status`

```json
{
  "researchId": "...",
  "fastApiResearchId": "RES_...",
  "status": "running",
  "currentStage": "fact_checking",
  "progress": 63
}
```

When FastAPI reports completed, Mongo session is updated with report/sources/claims/analysis.

### GET `/api/v1/research/:id`

Full session payload for the frontend (report, sources, claims, contradictions, analysis, charts).

### GET `/api/v1/research`

Query: `projectId`, `status`, `page`, `limit`

```json
{
  "items": [],
  "page": 1,
  "limit": 20,
  "total": 0
}
```

### GET `/api/v1/research/:id/sources`

### GET `/api/v1/research/:id/claims`

### GET `/api/v1/research/:id/report`

### POST `/api/v1/research/:id/save`

Marks a completed session as saved (reference only).

### DELETE `/api/v1/research/:id/save`

Errors: `RESEARCH_NOT_FOUND`, `RESEARCH_NOT_READY`, `PROJECT_NOT_FOUND`, `PROVIDER_UNAVAILABLE`, `TIMEOUT`

---

## Saved reports

### GET `/api/v1/saved-reports`

Auth: required

Returns lightweight saved-report references for the current user.

---

## Health

### GET `/health`

```json
{ "status": "ok", "service": "researchx-server" }
```

---

## Frontend flow

1. Register / login → store JWT  
2. Create project  
3. `POST /api/v1/research` with `projectId` + query  
4. Poll `GET /api/v1/research/:id/status`  
5. Load result / sources / claims / report  
6. Optionally save report  
7. Browse history via `GET /api/v1/research`
