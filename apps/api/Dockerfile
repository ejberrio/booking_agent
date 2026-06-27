# API (FastAPI) — imagen de producción basada en uv.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# uv (gestor de dependencias) desde la imagen oficial.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Instala dependencias primero (capa cacheable) usando el lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copia el código de la app.
COPY . .

# Migraciones + uvicorn (escucha en $PORT que provee Railway).
CMD ["sh", "scripts/start.sh"]
