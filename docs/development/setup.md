# Local setup

1. Clone repo and create Python venv at repo root: `python -m venv .venv`
2. `pip install -r apps/ai-service/requirements.txt`
3. `npm install` at repo root (workspaces)
4. Create `.env` at repo root (and under apps as needed) with Mongo URI + API keys — never commit these files
5. Start AI (8000), server (5000), web (5173) — see root README

Data directories under `data/` are created automatically on AI service startup.
