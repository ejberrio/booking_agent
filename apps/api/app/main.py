import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.observability import init_sentry, setup_logging

# Observabilidad: logging + Sentry (no-op sin DSN). Antes de crear la app.
setup_logging(settings.log_level)
init_sentry(settings.sentry_dsn, settings.environment, release="0.1.1")

_request_log = logging.getLogger("api.request")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Carga la caché de secretos (BD cifrada > entorno). Resiliente: si la BD no
    # responde o la tabla aún no existe, todo cae a variables de entorno.
    try:
        from app.db.session import SessionLocal
        from app.services import secret_service

        async with SessionLocal() as session:
            await secret_service.load_cache(session)
    except Exception:
        logging.getLogger("api.startup").warning(
            "no se pudo cargar la caché de secretos; se usan variables de entorno"
        )
    yield


app = FastAPI(
    title="StayLever API",
    version="0.1.2",
    lifespan=lifespan,
    description=(
        "Agente de IA para gestion de precios, disponibilidad y promociones en "
        "Booking.com y Airbnb via Channel Manager."
    ),
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
