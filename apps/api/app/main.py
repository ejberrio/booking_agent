import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.observability import init_sentry, setup_logging

# Observabilidad: logging + Sentry (no-op sin DSN). Antes de crear la app.
setup_logging(settings.log_level)
init_sentry(settings.sentry_dsn, settings.environment, release="0.1.1")

_request_log = logging.getLogger("api.request")

app = FastAPI(
    title="Booking AI Agent API",
    version="0.1.1",
    description="Agente de IA para gestion de precios y promociones en Booking.com.",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Registra una línea key=value por petición (path SIN query, sin secretos)."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        ms = int((time.perf_counter() - start) * 1000)
        _request_log.error(
            "method=%s path=%s status=500 ms=%d",
            request.method,
            request.url.path,
            ms,
            exc_info=True,
        )
        raise
    ms = int((time.perf_counter() - start) * 1000)
    _request_log.info(
        "method=%s path=%s status=%d ms=%d",
        request.method,
        request.url.path,
        response.status_code,
        ms,
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "booking-agent-api",
        "status": "ok",
        "version": app.version,
        "environment": settings.environment,
    }
