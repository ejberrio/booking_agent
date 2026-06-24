"""Servicio de eventos: upsert idempotente por dedup_key."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventKind, Relevance
from app.models.market import Event


def make_dedup_key(name: str, start: date, location: str | None) -> str:
    """Clave estable de deduplicación: nombre + fecha + lugar, normalizados."""
    loc = (location or "").strip().lower()
    return f"{name.strip().lower()}|{start.isoformat()}|{loc}"


async def upsert_event(
    session: AsyncSession,
    *,
    name: str,
    start_date: date,
    kind: EventKind,
    end_date: date | None = None,
    relevance: Relevance = Relevance.medium,
    location: str | None = None,
    source_url: str | None = None,
) -> Event:
    """Crea el evento o devuelve el existente si su dedup_key ya está registrado."""
    dedup_key = make_dedup_key(name, start_date, location)
    res = await session.execute(select(Event).where(Event.dedup_key == dedup_key))
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing

    event = Event(
        name=name,
        start_date=start_date,
        end_date=end_date,
        kind=kind,
        relevance=relevance,
        location=location,
        source_url=source_url,
        dedup_key=dedup_key,
    )
    session.add(event)
    await session.flush()
    return event
