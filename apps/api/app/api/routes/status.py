"""GET /status — foto de salud del sistema para el operador (resiliente).

Distinto de /health (liveness básico para Railway). Cada comprobación va aislada:
si una dependencia falla o tarda, se marca degradada y el endpoint responde igual.
El chequeo de Beds24 se cachea ~5 min para no consumir cuota por consulta.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.api.routes.sync import get_adapter
from app.core.config import settings
from app.db.session import SessionLocal
from app.services import sync_service

router = APIRouter()

VERSION = "0.1.1"
_BEDS24_TTL = 300  # 5 min
_beds24_cache: dict[str, object] = {"value": "unknown", "at": 0.0}


async def _db_status() -> str:
    try:
        async with asyncio.timeout(3):
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


async def _beds24_status() -> str:
    now = time.time()
    if _beds24_cache["value"] != "unknown" and now - float(_beds24_cache["at"]) < _BEDS24_TTL:
        return str(_beds24_cache["value"])
    result = "error"
    adapter = get_adapter()
    try:
        async with asyncio.timeout(8):
            async with SessionLocal() as session:
                conn = await sync_service.test_connection(session, adapter)
            result = "connected" if conn.status.value == "connected" else "error"
    except Exception:
        result = "error"
    finally:
        try:
            await adapter.aclose()
        except Exception:
            pass
    _beds24_cache["value"] = result
    _beds24_cache["at"] = now
    return result


async def _open_issues() -> int:
    try:
        async with asyncio.timeout(3):
            async with SessionLocal() as session:
                return len(await sync_service.list_open_issues(session))
    except Exception:
        return -1  # desconocido


@router.get("/status")
async def status():
    return {
        "version": VERSION,
        "environment": settings.environment,
        "db": await _db_status(),
        "beds24": await _beds24_status(),
        "open_issues": await _open_issues(),
    }
