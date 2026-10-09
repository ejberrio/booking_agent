"""Avisos de reservas de Beds24 en tiempo real (feature 020).

El aviso es solo una PISTA (qué reserva y qué fechas mirar): la verdad se trae de
Beds24 re-sincronizando el rango con `sync_service.import_remote`. Así los
duplicados y el desorden convergen solos y una clave filtrada no puede inyectar
datos. Del cuerpo se leen únicamente id/propertyId/arrival/departure; nunca se
guarda ni se registra (trae datos personales y tokens de pago).
"""

from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.booking import Booking
from app.models.enums import WebhookResult
from app.models.webhook import WebhookEvent
from app.services import push_service, secret_service, sync_service

KEY_SECRET = "beds24_webhook_key"
HEADER_NAME = "X-StayLever-Key"
ENDPOINT_URL = "https://staylever.com/api/hooks/beds24"
DEFAULT_WINDOW_DAYS = 90  # aviso sin fechas: ventana corta (el cron diario cubre el año)
RETENTION_DAYS = 30
IDLE_AFTER_DAYS = 7


@dataclass(frozen=True)
class BookingHint:
    booking_id: str | None = None
    property_id: str | None = None
    arrival: date | None = None
    departure: date | None = None


def verify_key(presented: str | None) -> Literal["ok", "missing_config", "invalid"]:
    expected = secret_service.get_secret(KEY_SECRET)
    if not expected:
        return "missing_config"
    if not presented or not hmac.compare_digest(presented.encode(), expected.encode()):
        return "invalid"
    return "ok"


def _as_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def parse_hint(raw: bytes) -> BookingHint:
    """Extrae la pista del cuerpo V2. Tolerante: nunca lanza; descarta todo lo demás."""
    try:
        data = json.loads(raw or b"{}")
    except (ValueError, UnicodeDecodeError):
        return BookingHint()
    booking = data.get("booking") if isinstance(data, dict) else None
    if not isinstance(booking, dict):
        return BookingHint()
    bid, pid = booking.get("id"), booking.get("propertyId")
    return BookingHint(
        booking_id=str(bid) if bid is not None else None,
        property_id=str(pid) if pid is not None else None,
        arrival=_as_date(booking.get("arrival")),
        departure=_as_date(booking.get("departure")),
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _record(
    session: AsyncSession,
    result: WebhookResult,
    *,
    booking_ref: str | None = None,
    detail: str | None = None,
    sync_run_id: int | None = None,
) -> WebhookEvent:
    await session.execute(
        delete(WebhookEvent).where(
            WebhookEvent.received_at < _now() - timedelta(days=RETENTION_DAYS)
        )
    )
    ev = WebhookEvent(
        result=result,
        booking_ref=(booking_ref or "")[:40] or None,
        detail=detail,
        sync_run_id=sync_run_id,
    )
    session.add(ev)
    await session.flush()
    return ev


async def record_rejected(session: AsyncSession) -> WebhookEvent:
    return await _record(session, WebhookResult.rejected, detail="clave inválida")


async def _sync_range(session: AsyncSession, hint: BookingHint, today: date) -> tuple[date, date]:
    """Rango a re-sincronizar: la estancia nueva ∪ la previa (si cambió de fechas)."""
    points: list[date] = [d for d in (hint.arrival, hint.departure) if d]
    if hint.booking_id:
        prev = (
            await session.execute(
                select(Booking.check_in, Booking.check_out).where(
                    Booking.external_ref == hint.booking_id
                )
            )
        ).first()
        if prev:
            points += [prev[0], prev[1]]
    if not points:
        return today, today + timedelta(days=DEFAULT_WINDOW_DAYS)
    return min(points), max(points)


async def handle(
    session: AsyncSession, adapter, hint: BookingHint, *, today: date | None = None
) -> WebhookEvent:
    """Procesa un aviso YA autenticado. Siempre deja un WebhookEvent; nunca lanza."""
    today = today or date.today()
    if hint.property_id and settings.beds24_prop_id and hint.property_id != str(
        settings.beds24_prop_id
    ):
        return await _record(session, WebhookResult.ignored, booking_ref=hint.booking_id)

    date_from, date_to = await _sync_range(session, hint, today)
    for attempt in range(2):
        events: list = []
        try:
            async with session.begin_nested():
                run = await sync_service.import_remote(
                    session, adapter, date_from, date_to, events=events
                )
            # Avisos al celular (feature 025): tolerante a fallos, nunca rompe el webhook.
            await push_service.notify_booking_events(session, events)
            return await _record(
                session, WebhookResult.accepted, booking_ref=hint.booking_id, sync_run_id=run.id
            )
        except IntegrityError:
            # Alta simultánea (aviso + cron) chocó con el índice único: el segundo
            # intento ya encuentra la reserva y la actualiza en vez de crearla.
            if attempt == 0:
                continue
            return await _record(
                session,
                WebhookResult.failed,
                booking_ref=hint.booking_id,
                detail="conflicto al guardar la reserva; el cron lo corregirá",
            )
        except Exception as exc:  # noqa: BLE001 — se registra el TIPO, nunca el mensaje
            return await _record(
                session,
                WebhookResult.failed,
                booking_ref=hint.booking_id,
                detail=f"Beds24 no respondió ({type(exc).__name__})",
            )
    raise AssertionError("inalcanzable")


async def status(session: AsyncSession, *, now: datetime | None = None) -> dict:
    now = now or _now()
    configured = bool(secret_service.get_secret(KEY_SECRET))
    since = now - timedelta(days=IDLE_AFTER_DAYS)
    counts = {r.value: 0 for r in WebhookResult}
    for result, n in (
        await session.execute(
            select(WebhookEvent.result, func.count())
            .where(WebhookEvent.received_at >= since)
            .group_by(WebhookEvent.result)
        )
    ).all():
        counts[WebhookResult(result).value] = n
    last = (
        await session.execute(
            select(func.max(WebhookEvent.received_at)).where(
                WebhookEvent.result == WebhookResult.accepted
            )
        )
    ).scalar()
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)  # SQLite devuelve naive
    if not configured:
        state = "unconfigured"
    elif last is None:
        state = "never"
    elif last < since:
        state = "idle"
    else:
        state = "active"
    return {
        "configured": configured,
        "status": state,
        "last_accepted_at": last.isoformat() if last else None,
        "counts_7d": counts,
        "endpoint_url": ENDPOINT_URL,
        "header_name": HEADER_NAME,
    }


async def generate_key(session: AsyncSession) -> tuple[str, str]:
    """Genera y guarda una clave nueva (rota la anterior). Devuelve (línea, pista):
    es la ÚNICA vez que el valor sale de la API (para pegarlo en Beds24)."""
    value = secrets.token_urlsafe(32)
    await secret_service.set_secret(session, KEY_SECRET, value)
    return f"{HEADER_NAME}: {value}", f"…{value[-4:]}"
