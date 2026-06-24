from fastapi import APIRouter

from app.api.routes import chat, health, sync

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
