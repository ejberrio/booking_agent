#!/bin/sh
# Arranque de la API en producción: aplica migraciones (idempotente) y lanza uvicorn.
set -e

echo "[start] aplicando migraciones (alembic upgrade head)…"
alembic upgrade head

echo "[start] iniciando uvicorn en :${PORT:-8000}"
# Bind a :: (IPv6, dual-stack) — requerido por la red privada de Railway
# (api.railway.internal resuelve a IPv6); también acepta IPv4 en Linux.
exec uvicorn app.main:app --host "::" --port "${PORT:-8000}"
