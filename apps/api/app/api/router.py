from fastapi import APIRouter

from app.api.routes import (
    bookings,
    calendar_notes,
    chat,
    health,
    hooks,
    pois,
    pricing,
    secrets,
    status,
    suggestions,
    sync,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(status.router, tags=["status"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(calendar_notes.router, prefix="/calendar-notes", tags=["calendar-notes"])
api_router.include_router(secrets.router, prefix="/settings/secrets", tags=["secrets"])
api_router.include_router(pois.router, tags=["pois"])  # /pois y /scan-config
api_router.include_router(hooks.router, prefix="/hooks", tags=["hooks"])  # feature 020
