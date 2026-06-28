from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title="Booking AI Agent API",
    version="0.1.1",
    description="Agente de IA para gestion de precios y promociones en Booking.com.",
)

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
