#!/bin/sh
# Arranque de la API en producción: aplica migraciones (idempotente) y lanza uvicorn.
set -e

echo "[start] aplicando migraciones (alembic upgrade head)…"
alembic upgrade head

echo "[start] iniciando uvicorn en :${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
