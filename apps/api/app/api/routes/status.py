"""GET /status — foto de salud del sistema para el operador (resiliente).

Distinto de /health (liveness básico para Railway). Cada comprobación va aislada:
si una dependencia falla o tarda, se marca degradada y el endpoint responde igual.
El chequeo de Beds24 se cachea ~5 min para no consumir cuota por consulta.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text

from app.api.routes.sync import get_adapter
from app.channels.factory import has_credentials
from app.core.config import settings
from app.core.context import RequestContext, require_ctx
from app.db.session import SessionLocal
from app.db.tenancy import tenant_session
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Channel
from app.services import sync_service

router = APIRouter()

VERSION = "0.1.2"
_BEDS24_TTL = 300  # 5 min
# Caché por cuenta (feature 026): {account_id: (valor, instante)}.
_beds24_cache: dict[int, tuple[str, float]] = {}


async def _db_status() -> str:
    try:
        async with asyncio.timeout(3):
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


async def _beds24_status(account_id: int) -> str:
    now = time.time()
    cached = _beds24_cache.get(account_id)
    if cached and now - cached[1] < _BEDS24_TTL:
        return cached[0]
    result = "error"
    try:
        async with asyncio.timeout(8):
            async with tenant_session(account_id) as session:
                if not has_credentials(session):
                    result = "unconfigured"  # cuenta sin channel manager (feature 026)
                else:
                    adapter = get_adapter(session)
                    try:
                        conn = await sync_service.test_connection(session, adapter)
                        await session.commit()
                    finally:
                        await adapter.aclose()
                    result = "connected" if conn.status.value == "connected" else "error"
    except Exception:
        result = "error"
    _beds24_cache[account_id] = (result, now)
    return result


async def _open_issues(account_id: int) -> int:
    try:
        async with asyncio.timeout(3):
            async with tenant_session(account_id) as session:
                return len(await sync_service.list_open_issues(session))
    except Exception:
        return -1  # desconocido


_CHANNEL_ORDER = [ChannelKind.booking, ChannelKind.airbnb, ChannelKind.direct]


async def _channels_status(account_id: int) -> list[dict]:
    """Canales registrados + reservas confirmadas por canal (feature 012).

    Mismo patrón resiliente del endpoint: si falla, [] y la respuesta sigue.
    Un kind sin fila Channel aparece solo si tiene reservas (is_active=False).
    """
    try:
        async with asyncio.timeout(3):
            async with tenant_session(account_id) as session:
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
async def status(ctx: RequestContext = Depends(require_ctx)):
    # Checks concurrentes: la latencia total es la del más lento, no la suma.
    acc = ctx.account_id
    db, beds24, open_issues, channels = await asyncio.gather(
        _db_status(), _beds24_status(acc), _open_issues(acc), _channels_status(acc)
    )
    return {
        "version": VERSION,
        "environment": settings.environment,
        "db": db,
        "beds24": beds24,
        "open_issues": open_issues,
        "channels": channels,
    }
