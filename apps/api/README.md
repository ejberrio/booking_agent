# API — Booking AI Agent (FastAPI)

Backend del agente de IA: orquestación del LLM, motor de precios y adaptadores de Channel Manager.

## Requisitos
- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/)

## Arranque
```bash
uv sync                 # instala dependencias
cp ../../.env.example .env   # (opcional) arranca sin .env en modo demo
uv run uvicorn app.main:app --reload --port 8000
```

- Salud: http://localhost:8000/health
- Docs (OpenAPI): http://localhost:8000/docs
- Chat (placeholder): `POST /chat  { "message": "..." }`

## Migraciones (Alembic)
```bash
uv run alembic revision --autogenerate -m "init"
uv run alembic upgrade head
```

## Tests / lint
```bash
uv run pytest -q
uv run ruff check .
```

## Estructura
```
app/
  core/config.py   # settings (env)
  api/routes/      # health, chat (crecerá: pricing, suggestions...)
  llm/client.py    # capa LLM provider-agnostic (LiteLLM)
  db/              # SQLAlchemy async (base, session)
migrations/        # Alembic
```
