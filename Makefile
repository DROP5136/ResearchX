# ResearchX — common developer commands
# Requires: Python venv at .venv/, Node 18+, MongoDB (local or Atlas)

.PHONY: install install-ai install-node dev-ai dev-server dev-web test test-ai test-server test-web lint build

install: install-ai install-node

install-ai:
	.\.venv\Scripts\pip.exe install -r apps/ai-service/requirements.txt

install-node:
	npm install

dev-ai:
	cd apps/ai-service && ..\..\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000

dev-server:
	npm run dev -w researchx-server

dev-web:
	npm run dev -w researchx-web

test: test-ai test-server test-web

test-ai:
	cd apps/ai-service && ..\..\.venv\Scripts\python.exe -m pytest -q

test-server:
	npm run test -w researchx-server

test-web:
	npm run test -w researchx-web

lint:
	npm run lint -w researchx-server
	npm run lint -w researchx-web

build:
	npm run build -w researchx-server
	npm run build -w researchx-web
