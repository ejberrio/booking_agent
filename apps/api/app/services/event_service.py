"""Servicio de eventos: upsert idempotente por (ciudad, dedup_key).

Feature 026: los eventos son datos PÚBLICOS de una ciudad, compartidos entre cuentas.
"""

from __future__ import annotations

import unicodedata
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventKind, Relevance
from app.models.market import Event


DEFAULT_CITY = "Medellín"


def normalize_city(city: str | None) -> str:
    """'Medellín, Antioquia' → 'medellin' (minúsculas, sin tildes, sin región)."""
    base = (city or DEFAULT_CITY).split(",")[0].strip() or DEFAULT_CITY
    plain = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().split())


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
    city: str | None = None,
) -> Event:
    """Crea el evento o devuelve el existente si su (ciudad, dedup_key) ya está registrado."""
    city_key = normalize_city(city)
    dedup_key = make_dedup_key(name, start_date, location)
    res = await session.execute(
        select(Event).where(Event.city == city_key, Event.dedup_key == dedup_key)
    )
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
        city=city_key,
    )
    session.add(event)
    await session.flush()
    return event
