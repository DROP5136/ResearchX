# Testing

## AI service

```powershell
cd apps\ai-service
..\..\.venv\Scripts\python.exe -m pytest -q
```

Unit tests: `tests/unit/`  
Integration tests: `tests/integration/`

## Server

```powershell
npm run test -w researchx-server
```

Uses mongodb-memory-server + Jest.

## Web

```powershell
npm run test -w researchx-web
```

Vitest + Testing Library.
