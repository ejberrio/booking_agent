"""GET /status — foto de salud del sistema para el operador (resiliente).

Distinto de /health (liveness básico para Railway). Cada comprobación va aislada:
si una dependencia falla o tarda, se marca degradada y el endpoint responde igual.
El chequeo de Beds24 se cachea ~5 min para no consumir cuota por consulta.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.api.routes.sync import get_adapter
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Channel
from app.services import sync_service

router = APIRouter()

VERSION = "0.1.2"
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


_CHANNEL_ORDER = [ChannelKind.booking, ChannelKind.airbnb, ChannelKind.direct]


async def _channels_status() -> list[dict]:
    """Canales registrados + reservas confirmadas por canal (feature 012).

    Mismo patrón resiliente del endpoint: si falla, [] y la respuesta sigue.
    Un kind sin fila Channel aparece solo si tiene reservas (is_active=False).
    """
    try:
        async with asyncio.timeout(3):
            async with SessionLocal() as session:
                ch_rows = (await session.execute(select(Channel))).scalars().all()
                cnt_rows = (
                    await session.execute(
                        select(Booking.channel_kind, func.count())
                        .where(Booking.status == BookingStatus.confirmed)
                        .group_by(Booking.channel_kind)
                    )
                ).all()
        active = {c.kind: c.is_active for c in ch_rows}
        counts = {kind: int(n) for kind, n in cnt_rows}
        return [
            {
                "kind": kind.value,
                "is_active": bool(active.get(kind, False)),
                "bookings": counts.get(kind, 0),
            }
            for kind in _CHANNEL_ORDER
            if kind in active or counts.get(kind, 0) > 0
        ]
    except Exception:
        return []


@router.get("/status")
async def status():
    # Checks concurrentes: la latencia total es la del más lento, no la suma.
    db, beds24, open_issues, channels = await asyncio.gather(
        _db_status(), _beds24_status(), _open_issues(), _channels_status()
    )
    return {
        "version": VERSION,
        "environment": settings.environment,
        "db": db,
        "beds24": beds24,
        "open_issues": open_issues,
        "channels": channels,
    }
