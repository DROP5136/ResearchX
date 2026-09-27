# ResearchX security model

## Authentication

- Users register/login via Express (`POST /api/v1/auth/*`).
- Passwords are hashed with **bcrypt** (cost 12); never returned in API responses.
- Sessions use **JWT** (`Authorization: Bearer <token>`), signed with `JWT_SECRET`, with expiry (`JWT_EXPIRES_IN`).
- Identity is taken only from the verified token (`req.userId`), never from client-supplied `userId` fields.

## Authorization

Every resource query is scoped by ownership:

- Projects, research sessions, documents, saved reports filter by `userId` from the JWT.
- Cross-user access returns **404** (not 403) to avoid resource enumeration.

## Express ↔ FastAPI

- Express is the public API. FastAPI should listen on `127.0.0.1` only.
- When `AI_SERVICE_TOKEN` / `ai_service_token` is set, FastAPI requires header `X-Internal-Token`.
- In `production`, the token is **required** on both sides.
- OpenAPI `/docs` is disabled when `app_env=production`.

## API security

- Helmet security headers (CSP disabled on API to avoid breaking separate SPA origins).
- CORS allowlist via `CORS_ORIGIN` (never `*` by default).
- JSON body limit: **1mb**.
- Global rate limit + stricter limits for auth, research create, and uploads.
- Structured errors: `{ error: { code, message } }` — no stack traces or filesystem paths to clients.
- `X-Request-Id` on responses for correlation.

## Prompt injection

Untrusted inputs (user query, web pages, PDF text, search snippets, RAG chunks) are labeled in agent prompts as **UNTRUSTED DATA**.

- System prompts stay separate from user/external content.
- Extractor/writer use evidence grounding; planner wraps the query in explicit untrusted markers.
- Malicious PDF/HTML text such as “ignore previous instructions” is treated as content, not instructions.

## Document / PDF security

- Auth + project ownership required.
- Extension must be `.pdf`; magic bytes `%PDF-` checked.
- Size and per-project document caps via env.
- Storage keys use generated safe filenames under `data/documents/{userId}/{projectId}/`.
- Path traversal blocked; AI service confines process paths to `documents_dir`.
- Files are not publicly served.

## SSRF protections

`WebpageLoader` only fetches `http`/`https` URLs after validation:

- Blocks `file://`, localhost, private/link-local/reserved IPs, metadata hosts.
- Re-validates the final URL after redirects.

## Rate limits & resource limits

| Area | Env knobs |
|------|-----------|
| Global | `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW_MS` |
| Auth | `AUTH_RATE_LIMIT_MAX` |
| Research | `RESEARCH_RATE_LIMIT_MAX` |
| Upload | `UPLOAD_RATE_LIMIT_MAX` |
| PDF size / count | `MAX_UPLOAD_BYTES`, `MAX_DOCS_PER_PROJECT` |
| PDF pages | `MAX_PDF_PAGES` (AI) |
| Concurrent AI jobs | `MAX_CONCURRENT_RESEARCH_JOBS` |

## Mock mode & evaluation

- Client `mockMode` is honored only when `ALLOW_MOCK_MODE` is true (default: non-production).
- Evaluation routes require `ALLOW_EVALUATION` (default: non-production).

## Secrets

- Never commit `.env` (gitignored).
- Frontend may only use public `VITE_*` vars (e.g. `VITE_API_URL`).
- Do not log passwords, JWTs, or API keys.

## Known limitations

- JWT stored in `localStorage` (XSS risk if the SPA is compromised); httpOnly cookies not implemented.
- FastAPI is open when `AI_SERVICE_TOKEN` is empty in development — keep it bound to localhost.
- No OCR; scanned PDFs rejected as empty.
- Dependency upgrades should be reviewed case-by-case (`npm audit` / pip tooling).
