from fastapi import APIRouter, Depends

from app.api.routes import (
    account,
    bookings,
    calendar_notes,
    chat,
    health,
    hooks,
    pois,
    preferences,
    pricing,
    push,
    secrets,
    status,
    suggestions,
    sync,
)
from app.core.context import require_ctx

# Feature 026: toda ruta con datos exige el contexto de una cuenta (principio VI).
# Sin contexto: health (liveness) y hooks (la clave del aviso identifica la cuenta).
_ctx = [Depends(require_ctx)]

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(status.router, tags=["status"], dependencies=_ctx)
api_router.include_router(chat.router, prefix="/chat", tags=["chat"], dependencies=_ctx)
api_router.include_router(sync.router, prefix="/sync", tags=["sync"], dependencies=_ctx)
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"], dependencies=_ctx)
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"], dependencies=_ctx)
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"], dependencies=_ctx)
api_router.include_router(calendar_notes.router, prefix="/calendar-notes", tags=["calendar-notes"], dependencies=_ctx)
api_router.include_router(secrets.router, prefix="/settings/secrets", tags=["secrets"], dependencies=_ctx)
api_router.include_router(pois.router, tags=["pois"], dependencies=_ctx)  # /pois y /scan-config
api_router.include_router(hooks.router, prefix="/hooks", tags=["hooks"])  # feature 020
api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"], dependencies=_ctx)  # 021
api_router.include_router(push.router, prefix="/push", tags=["push"], dependencies=_ctx)  # 025
api_router.include_router(account.router, tags=["account"], dependencies=_ctx)  # 026
