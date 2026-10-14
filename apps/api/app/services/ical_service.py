"""Ocupación desde los calendarios iCal de exportación (feature 029, modo sin conexión).

Airbnb y Booking.com publican un enlace iCal (solo lectura) con las noches ocupadas. StayLever
lo lee para no sugerir precios en noches vendidas:

- Reservas → `Booking` con canal de origen, sin nombre del huésped (el iCal no lo trae y no
  lo necesitamos: feature 028). Las que desaparecen del calendario quedan canceladas.
- Bloqueos ("Not available", "Closed") → noche bloqueada en `CalendarDay`.

Seguridad: solo se descargan enlaces https de dominios conocidos (Airbnb, Booking, Vrbo,
Google Calendar), sin seguir redirecciones a otros dominios, con tiempo y tamaño máximos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Channel, Property, UnitType

ALLOWED_HOSTS = (
    "airbnb.com", "airbnb.com.co", "airbnb.com.br", "airbnb.mx", "airbnb.es", "airbnb.co.uk",
    "booking.com", "vrbo.com", "homeaway.com", "calendar.google.com",
)
MAX_BYTES = 1_000_000
TIMEOUT = 15
HORIZON_DAYS = 400
_BLOCK_WORDS = ("not available", "closed", "blocked", "no disponible", "bloquead")


class IcalError(ValueError):
    pass


@dataclass(frozen=True)
class IcalEvent:
    uid: str
    start: date
    end: date  # exclusiva (como en iCal: la salida no ocupa)
    summary: str = ""

    @property
    def blocked(self) -> bool:
        s = self.summary.lower()
        return any(w in s for w in _BLOCK_WORDS)


@dataclass
class SyncReport:
    channels: int = 0
    bookings: int = 0
    cancelled: int = 0
    blocked_nights: int = 0
    errors: list[str] = field(default_factory=list)


def allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == h or host.endswith("." + h) for h in ALLOWED_HOSTS
    )


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_date(value: str) -> date | None:
    m = re.match(r"(\d{8})", value.strip())
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def parse(text: str) -> list[IcalEvent]:
    """Parser mínimo de VEVENT (DTSTART/DTEND/UID/SUMMARY), suficiente para Airbnb/Booking."""
    events: list[IcalEvent] = []
    cur: dict[str, str] | None = None
    for line in _unfold(text):
        if line.startswith("BEGIN:VEVENT"):
            cur = {}
        elif line.startswith("END:VEVENT") and cur is not None:
            start, end = _parse_date(cur.get("DTSTART", "")), _parse_date(cur.get("DTEND", ""))
            if start and (end is None or end <= start):
                end = start + timedelta(days=1)
            if start and end:
                uid = cur.get("UID") or f"{start.isoformat()}-{end.isoformat()}"
                events.append(IcalEvent(uid[:80], start, end, cur.get("SUMMARY", "")))
            cur = None
        elif cur is not None and ":" in line:
            key, value = line.split(":", 1)
            cur[key.split(";", 1)[0].upper()] = value.strip()
    return events


async def fetch(url: str, transport: httpx.AsyncBaseTransport | None = None) -> str:
    if not allowed(url):
        raise IcalError("enlace iCal no permitido (usa el de exportación de Airbnb o Booking).")
    async with httpx.AsyncClient(timeout=TIMEOUT, transport=transport, follow_redirects=False) as c:
        resp = await c.get(url)
    if resp.status_code != 200:
        raise IcalError(f"el calendario respondió {resp.status_code}")
    if len(resp.content) > MAX_BYTES:
        raise IcalError("el calendario es demasiado grande")
    return resp.text


async def _apply(
    session: AsyncSession, unit: UnitType, kind: ChannelKind, events: list[IcalEvent],
    today: date, report: SyncReport,
) -> None:
    horizon = today + timedelta(days=HORIZON_DAYS)
    prefix = f"ical:{kind.value}:"
    seen: set[str] = set()
    for ev in events:
        if ev.end <= today or ev.start > horizon:
            continue
        if ev.blocked:
            d = max(ev.start, today)
            while d < ev.end and d <= horizon:
                day = (
                    await session.execute(
                        select(CalendarDay).where(
                            CalendarDay.unit_type_id == unit.id, CalendarDay.date == d
                        )
                    )
                ).scalar_one_or_none()
                if day is None:
                    session.add(CalendarDay(unit_type_id=unit.id, date=d, units_available=0,
                                            is_blocked=True))
                elif not day.is_blocked:
                    day.is_blocked = True
                report.blocked_nights += 1
                d += timedelta(days=1)
            continue
        ref = (prefix + ev.uid)[:120]
        seen.add(ref)
        row = (
            await session.execute(select(Booking).where(Booking.external_ref == ref))
        ).scalar_one_or_none()
        if row is None:
            session.add(Booking(unit_type_id=unit.id, channel_kind=kind, check_in=ev.start,
                                check_out=ev.end, status=BookingStatus.confirmed,
                                external_ref=ref, guest_name=None))
            report.bookings += 1
        else:
            row.check_in, row.check_out = ev.start, ev.end
            row.status = BookingStatus.confirmed
    # Lo que ya no está en el calendario (futuro) se cancela.
    stale = (
        await session.execute(
            select(Booking).where(
                Booking.unit_type_id == unit.id,
                Booking.external_ref.like(prefix + "%"),
                Booking.status == BookingStatus.confirmed,
                Booking.check_out > today,
            )
        )
    ).scalars()
    for b in stale:
        if b.external_ref not in seen:
            b.status = BookingStatus.cancelled
            report.cancelled += 1


async def sync_account(
    session: AsyncSession, *, today: date | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SyncReport:
    """Lee los iCal de todos los apartamentos sin conexión de la cuenta del contexto."""
    today = today or date.today()
    report = SyncReport()
    rows = (
        await session.execute(
            select(Channel, UnitType)
            .join(Property, Channel.property_id == Property.id)
            .join(UnitType, UnitType.property_id == Property.id)
            .where(Property.provider == "manual", Channel.ical_url.is_not(None))
        )
    ).all()
    for channel, unit in rows:
        report.channels += 1
        try:
            text = await fetch(channel.ical_url, transport)
            await _apply(session, unit, channel.kind, parse(text), today, report)
        except (IcalError, httpx.HTTPError) as exc:
            # Solo el tipo y el canal: la URL del iCal es privada (da acceso al calendario).
            msg = str(exc) if isinstance(exc, IcalError) else type(exc).__name__
            report.errors.append(f"{channel.kind.value}: {msg}")
    await session.flush()
    return report
