# Local setup

1. Clone repo and create Python venv at repo root: `python -m venv .venv`
2. `pip install -r apps/ai-service/requirements.txt`
3. `npm install` at repo root (workspaces)
4. Copy `.env.example` files under each app; set Mongo URI and API keys
5. Start AI (8000), server (5000), web (5173) — see root README

Data directories under `data/` are created automatically on AI service startup.
