# ResearchX AI Service

Python FastAPI + LangGraph research engine.

## Run

```powershell
cd apps/ai-service
..\..\.venv\Scripts\Activate.ps1
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

## Test

```powershell
python -m pytest -q
```

## Package layout

All importable code lives under `app/` (`from app.agents...`, `from app.api.main import app`).
