from fastapi import APIRouter

from app.api.routes import chat, health, pricing, status, suggestions, sync

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(status.router, tags=["status"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
