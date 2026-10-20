"""Percentiles de precio del mercado por zona, habitaciones y fecha (feature 038).

Fuente inicial: PriceLabs Market Dashboard → "Precios Futuros" (precio por noche SIN cargos,
p25/p50/p75/p90), que el administrador de plataforma importa por zona. Son datos agregados de
plataforma: no hay anuncios ni personas.

Uso: techo de las sugerencias (p90) y aviso cuando un precio queda por encima del mercado.
La zona es la ciudad principal del área metropolitana (Sabaneta → Medellín), como los eventos.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import municipalities
from app.domain.suggestion import MarketCap
from app.models.market import MarketBand
from app.models.property import UnitType

_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
          "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5}


def unit_bedrooms(unit: UnitType) -> int | None:
    """Habitaciones de la unidad: el campo, o deducidas del nombre ("Three-Bedroom", "3BR")."""
    if unit.bedrooms:
        return unit.bedrooms
    name = (unit.name or "").lower()
    m = re.search(r"(\d+)\s*(?:br\b|bed|hab|dorm|alcob)", name)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(" + "|".join(_WORDS) + r")[\s-]*(?:bedroom|habitaci|alcoba|dormitorio)", name)
    return _WORDS[m.group(1)] if m else None


def _dec(v) -> Decimal | None:
    if v is None or v == "":
        return None
    return Decimal(str(round(float(v))))


async def import_rows(session: AsyncSession, *, city: str, bedrooms: int, rows: list,
                      source: str = "pricelabs") -> int:
    """`rows` = [[fecha, p25, p50, p75, p90], …] (o dicts con esas claves). Reemplaza por fecha."""
    key = municipalities.area_core_key(city)
    n = 0
    for r in rows:
        if isinstance(r, dict):
            d, p25, p50, p75, p90 = (r.get("date") or r.get("day"), r.get("p25"), r.get("p50"),
                                     r.get("p75"), r.get("p90"))
        else:
            d, p25, p50, p75, p90 = (list(r) + [None] * 5)[:5]
        day = date.fromisoformat(str(d)[:10])
        if _dec(p90) is None:
            continue
        band = (
            await session.execute(
                select(MarketBand).where(MarketBand.city == key, MarketBand.bedrooms == bedrooms,
                                         MarketBand.day == day)
            )
        ).scalar_one_or_none()
        if band is None:
            band = MarketBand(city=key, bedrooms=bedrooms, day=day)
            session.add(band)
        band.p25, band.p50, band.p75, band.p90 = _dec(p25), _dec(p50), _dec(p75), _dec(p90)
        band.source = source[:40]
        n += 1
    await session.flush()
    return n


async def caps_for(session: AsyncSession, city: str | None, bedrooms: int | None,
                   date_from: date, date_to: date) -> dict[date, MarketCap]:
    """Techo por noche para la zona de la propiedad. Usa las habitaciones exactas; si no hay
    datos para ese tamaño, los de "todas" (0). Sin datos → {} (no hay techo)."""
    key = municipalities.area_core_key(city)
    rows = (
        await session.execute(
            select(MarketBand).where(MarketBand.city == key, MarketBand.day >= date_from,
                                     MarketBand.day <= date_to,
                                     MarketBand.bedrooms.in_([bedrooms or 0, 0]))
        )
    ).scalars().all()
    out: dict[date, MarketCap] = {}
    for b in sorted(rows, key=lambda b: b.bedrooms == 0):  # primero el tamaño exacto
        if b.day in out or b.p90 is None:
            continue
        out[b.day] = MarketCap(p90=b.p90, p75=b.p75, p50=b.p50,
                               bedrooms=b.bedrooms or None, source=b.source)
    return out


async def summary(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(MarketBand))).scalars().all()
    agg: dict[tuple, dict] = {}
    for b in rows:
        k = (b.city, b.bedrooms, b.source)
        a = agg.setdefault(k, {"city": b.city, "bedrooms": b.bedrooms, "source": b.source,
                               "days": 0, "from": b.day, "to": b.day})
        a["days"] += 1
        a["from"], a["to"] = min(a["from"], b.day), max(a["to"], b.day)
    return [{**a, "from": a["from"].isoformat(), "to": a["to"].isoformat()} for a in agg.values()]
