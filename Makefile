.PHONY: help setup db-up db-down api web dev test lint

help:
	@echo "Comandos:"
	@echo "  make setup    - instala dependencias (api + web)"
	@echo "  make db-up    - levanta Postgres (docker compose)"
	@echo "  make db-down  - detiene Postgres"
	@echo "  make api      - corre la API (FastAPI) en :8000"
	@echo "  make web      - corre la web (Next.js) en :3000"
	@echo "  make test     - corre los tests de la API"
	@echo "  make lint     - lint de api (ruff) y web (next lint)"

setup:
	cd apps/api && uv sync
	cd apps/web && npm install

db-up:
	docker compose up -d db

db-down:
	docker compose down

api:
	cd apps/api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd apps/web && npm run dev

test:
	cd apps/api && uv run pytest -q

lint:
	cd apps/api && uv run ruff check .
	cd apps/web && npm run lint
