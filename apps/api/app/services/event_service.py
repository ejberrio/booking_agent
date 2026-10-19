"""Servicio de eventos: upsert idempotente por (ciudad, dedup_key).

Feature 026: los eventos son datos PÚBLICOS de una ciudad, compartidos entre cuentas.
"""

from __future__ import annotations

import unicodedata
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventKind, Relevance
from app.models.market import Event
from app.models.mixins import _now


DEFAULT_CITY = "Medellín"


def normalize_city(city: str | None) -> str:
    """'Medellín, Antioquia' → 'medellin' (minúsculas, sin tildes, sin región)."""
    base = (city or DEFAULT_CITY).split(",")[0].strip() or DEFAULT_CITY
    plain = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().split())


def name_key(name: str) -> str:
    """Nombre comparable entre fuentes: 'Beéle — Borondo Tour' == 'Beele - borondo tour'."""
    import re

    plain = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def _rank(ev) -> tuple:
    """Mejor versión de un evento: la de una fuente oficial, luego la más importante."""
    rel = {"low": 0, "medium": 1, "high": 2}.get(getattr(ev.relevance, "value", ev.relevance), 0)
    official = bool(ev.source_url) and not str(ev.source_url).startswith("reportado:")
    return (not official, not ev.source_url, -rel, ev.id or 0)


def unique_events(events):
    """Un evento por (nombre parecido, fecha): el mismo visto en dos ciudades del área o con
    otro nombre ("Martin Garrix" / "Martin Garrix Show"). Conserva el orden de llegada y elige
    la mejor versión de cada grupo (`_rank`)."""
    return [min(g, key=_rank) for g in event_groups(events)]


def event_groups(events) -> list[list]:
    """Agrupa por fecha y nombre parecido a CUALQUIERA del grupo ("Juanes" ~ "Concierto de
    Juanes" ~ "Juanes · World Tour 2026")."""
    groups: list[list] = []
    for ev in events:
        for g in groups:
            if g[0].start_date == ev.start_date and any(
                similar_names(m.name, ev.name) for m in g
            ):
                g.append(ev)
                break
        else:
            groups.append([ev])
    return groups


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
    if existing is None:
        # Feature 034: el mismo evento con otro nombre ("Hebert Vargas · Éxito tras Éxito" de la
        # boletera vs "Concierto de Hebert Vargas" de una búsqueda) no se duplica.
        # En toda el área metropolitana (034/036): Hebert Vargas en Sabaneta = en Medellín.
        from app.domain import municipalities

        existing = await _similar(session, municipalities.area_keys(city_key), start_date, name)
    if existing is not None:
        if source_url and not existing.source_url:
            existing.source_url = source_url[:500]
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


_REL_RANK = {Relevance.low: 0, Relevance.medium: 1, Relevance.high: 2}


def similar_names(a: str, b: str) -> bool:
    ka, kb = name_key(a), name_key(b)
    if not ka or not kb:
        return False
    if ka == kb or (min(len(ka), len(kb)) >= 6 and (ka in kb or kb in ka)):
        return True
    ta, tb = set(ka.split()), set(kb.split())
    stop = {"de", "la", "el", "en", "y", "los", "las", "concierto", "tour", "2026", "2027"}
    ta, tb = ta - stop, tb - stop
    return bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) >= 0.6


async def _similar(session: AsyncSession, cities: list[str], start: date, name: str):
    rows = (
        await session.execute(
            select(Event).where(Event.city.in_(cities), Event.start_date == start)
        )
    ).scalars().all()
    return next((e for e in rows if similar_names(e.name, name)), None)


async def upsert_structured(
    session: AsyncSession, *, name: str, start_date: date, end_date: date | None,
    kind: EventKind, relevance: Relevance, location: str | None, source_url: str,
    city: str, area: list[str],
) -> Event:
    """Evento de una fuente estructurada (boletera/agenda): manda sobre lo extraído por la IA.

    Busca por enlace, luego por nombre parecido el mismo día en el área; actualiza fechas,
    recinto, municipio y relevancia (nunca la baja). Si no existe, lo crea.
    """
    ev = (
        await session.execute(select(Event).where(Event.source_url == source_url[:500]))
    ).scalars().first() or await _similar(session, area, start_date, name)
    if ev is None:
        return await upsert_event(
            session, name=name, start_date=start_date, end_date=end_date, kind=kind,
            relevance=relevance, location=location, source_url=source_url, city=city,
        )
    ev.name = name[:300]  # el nombre oficial de la boletera manda sobre el de la IA
    ev.start_date, ev.end_date = start_date, end_date
    loc = location or ev.location
    ev.location = loc[:300] if loc else None
    ev.source_url = source_url[:500]
    ev.city = normalize_city(city)
    if kind is not EventKind.other:
        ev.kind = kind
    if _REL_RANK[relevance] > _REL_RANK.get(ev.relevance, 0):
        ev.relevance = relevance
    ev.updated_at = _now()
    await session.flush()
    return ev


async def delete_by_source(session: AsyncSession, source_url: str) -> int:
    """Evento cancelado en la boletera: se borra (no debe empujar precios)."""
    rows = (
        await session.execute(select(Event).where(Event.source_url == source_url[:500]))
    ).scalars().all()
    for ev in rows:
        await session.delete(ev)
    return len(rows)


async def seen_recently(session: AsyncSession, source_url: str, *, days: int) -> bool:
    ev = (
        await session.execute(select(Event).where(Event.source_url == source_url[:500]))
    ).scalars().first()
    return ev is not None and _aware(ev.updated_at) > _now() - timedelta(days=days)


def _aware(dt):
    from datetime import UTC

    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def dedupe_area(session: AsyncSession, keys: list[str], today: date,
                      *, window_days: int = 10) -> dict:
    """Limpieza de eventos repetidos o con fecha equivocada en un área (feature 036).

    1. Mismo día y nombre parecido → se queda la mejor versión (fuente oficial, luego la más
       importante); completa recinto y fecha de fin si le faltaban.
    2. Un evento encontrado por búsqueda (sin enlace oficial) con nombre parecido a uno de una
       boletera en otra fecha cercana (±10 días) → fecha equivocada: se borra.
    Los festivos no se tocan.
    """
    rows = (
        await session.execute(
            select(Event).where(Event.city.in_(keys), Event.start_date >= today,
                                Event.kind != EventKind.holiday)
            .order_by(Event.start_date, Event.id)
        )
    ).scalars().all()
    merged = wrong_date = 0
    alive = []
    for group in event_groups(rows):
        keep = min(group, key=_rank)
        for d in group:
            if d is keep:
                continue
            keep.end_date = keep.end_date or d.end_date
            keep.location = keep.location or d.location
            if _REL_RANK.get(d.relevance, 0) > _REL_RANK.get(keep.relevance, 0):
                keep.relevance = d.relevance
            await session.delete(d)
            merged += 1
        alive.append(keep)
    # Fecha equivocada: solo conciertos grandes de una boletera (una sola noche). Ballet,
    # teatro o congresos pueden tener varias funciones y no se tocan.
    official = [e for e in alive if _rank(e)[0] is False and e.kind is EventKind.concert
                and e.relevance is Relevance.high]
    for e in alive:
        if e.source_url or e.kind is not EventKind.concert:
            continue
        for o in official:
            gap = abs((o.start_date - e.start_date).days)
            if 0 < gap <= window_days and similar_names(o.name, e.name):
                await session.delete(e)
                wrong_date += 1
                break
    await session.flush()
    return {"merged": merged, "wrong_date": wrong_date}
