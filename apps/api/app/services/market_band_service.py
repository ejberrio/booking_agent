"""Percentiles de precio del mercado por zona, habitaciones y fecha (feature 038).

Fuente inicial: PriceLabs Market Dashboard → "Precios Futuros" (precio por noche SIN cargos,
p25/p50/p75/p90), que el administrador de plataforma carga por zona y habitaciones subiendo el
CSV desde Administración (feature 040). Son datos agregados de plataforma: no hay anuncios ni
personas.

Uso: techo de las sugerencias (p90) y aviso cuando un precio queda por encima del mercado.
La zona es la ciudad principal del área metropolitana (Sabaneta → Medellín), como los eventos.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
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


MAX_DAYS_AHEAD = 400  # PriceLabs publica ~1 año hacia adelante
_DATE_HEAD = re.compile(r"^(dates?|fechas?|d[ií]a|stay ?dates?)$", re.I)
_PCT_HEAD = re.compile(r"(?:\b(25|50|75|90)(?:th|º|°)?\b.*percentil|percentil\w*\D*(25|50|75|90)\b)", re.I)


class CsvError(ValueError):
    pass


@dataclass
class ParsedCsv:
    rows: list[list] = field(default_factory=list)  # [[fecha, p25, p50, p75, p90], …] desde hoy
    past: int = 0  # filas de fechas pasadas (historial que trae el CSV): se ignoran
    invalid: int = 0  # filas sin fecha o con percentiles vacíos o desordenados


def _num(v: str) -> float | None:
    v = (v or "").strip().replace("$", "").replace(" ", "")
    if not v or v.lower() in {"nan", "none", "-", "-na", "n/a"}:
        return None
    if "," in v and "." not in v:  # 157260,5 → 157260.5
        v = v.replace(",", ".")
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def parse_csv(text: str, today: date | None = None) -> ParsedCsv:
    """Lee el CSV de PriceLabs → "Precios Futuros" → Descargar CSV.

    Encabezado esperado: `Dates, 25th Percentile, 50th Percentile, 75th Percentile,
    90th Percentile, …` (también en español: "Fecha", "Percentil 25"…). Las columnas se
    reconocen por nombre, así que el orden y las columnas extra no importan. Se guardan solo
    las fechas desde hoy (el CSV trae también ~2 años de historial).
    """
    today = today or date.today()
    text = (text or "").lstrip("\ufeff")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise CsvError("El archivo está vacío o no tiene filas de datos.")
    try:
        dialect = csv.Sniffer().sniff(lines[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO("\n".join(lines)), dialect)
    header = [h.strip() for h in next(reader)]
    date_col = next((i for i, h in enumerate(header) if _DATE_HEAD.match(h)), None)
    cols: dict[int, int] = {}
    for i, h in enumerate(header):
        m = _PCT_HEAD.search(h)
        if m:
            cols.setdefault(int(m.group(1) or m.group(2)), i)
    missing = [str(p) for p in (25, 50, 75, 90) if p not in cols]
    if date_col is None or missing:
        raise CsvError(
            "No reconozco el archivo: debe ser el CSV de \"Precios Futuros\" de PriceLabs, con "
            "las columnas Dates y 25th/50th/75th/90th Percentile"
            + (f" (faltan: {', '.join(missing)})" if missing else "") + "."
        )
    out = ParsedCsv()
    horizon = today.toordinal() + MAX_DAYS_AHEAD
    for r in reader:
        try:
            day = date.fromisoformat(r[date_col].strip()[:10])
        except (IndexError, ValueError):
            out.invalid += 1
            continue
        if day < today:
            out.past += 1
            continue
        if day.toordinal() > horizon:
            continue
        vals = [_num(r[cols[p]]) if cols[p] < len(r) else None for p in (25, 50, 75, 90)]
        if any(v is None or v <= 0 for v in vals) or vals != sorted(vals):
            out.invalid += 1
            continue
        out.rows.append([day.isoformat(), *vals])
    if not out.rows:
        raise CsvError("El archivo no trae fechas desde hoy en adelante con los cuatro percentiles.")
    return out


async def import_rows(session: AsyncSession, *, city: str, bedrooms: int, rows: list,
                      source: str = "pricelabs") -> int:
    """`rows` = [[fecha, p25, p50, p75, p90], …] (o dicts con esas claves). Reemplaza por fecha.

    Una sola consulta trae las fechas que ya existen y todo se guarda en un único flush: un año
    de fechas (~360) carga en un instante en vez de una consulta por fecha (feature 040).
    """
    key = municipalities.area_core_key(city)
    now = datetime.now(UTC)
    parsed: dict[date, tuple] = {}
    for r in rows:
        if isinstance(r, dict):
            d, p25, p50, p75, p90 = (r.get("date") or r.get("day"), r.get("p25"), r.get("p50"),
                                     r.get("p75"), r.get("p90"))
        else:
            d, p25, p50, p75, p90 = (list(r) + [None] * 5)[:5]
        day = date.fromisoformat(str(d)[:10])
        if _dec(p90) is None:
            continue
        parsed[day] = (_dec(p25), _dec(p50), _dec(p75), _dec(p90))
    if not parsed:
        return 0
    existing = {
        b.day: b
        for b in (
            await session.execute(
                select(MarketBand).where(
                    MarketBand.city == key, MarketBand.bedrooms == bedrooms,
                    MarketBand.day >= min(parsed), MarketBand.day <= max(parsed),
                )
            )
        ).scalars()
    }
    for day, (p25, p50, p75, p90) in parsed.items():
        band = existing.get(day)
        if band is None:
            band = MarketBand(city=key, bedrooms=bedrooms, day=day)
            session.add(band)
        band.p25, band.p50, band.p75, band.p90 = p25, p50, p75, p90
        band.source = source[:40]
        band.updated_at = now
    await session.flush()
    return len(parsed)


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


async def delete_zone(session: AsyncSession, *, city: str, bedrooms: int) -> int:
    """Borra los percentiles de una zona y tamaño (p. ej. si se cargó el filtro equivocado)."""
    key = municipalities.area_core_key(city)
    res = await session.execute(
        delete(MarketBand).where(MarketBand.city == key, MarketBand.bedrooms == bedrooms)
    )
    await session.flush()
    return res.rowcount or 0


async def summary(session: AsyncSession, today: date | None = None) -> list[dict]:
    """Una fila por zona y tamaño: fechas cubiertas desde hoy, rango, mediana típica y última
    carga (para ver si hay que refrescar)."""
    today = today or date.today()
    q = (
        select(MarketBand.city, MarketBand.bedrooms, MarketBand.source,
               func.count(MarketBand.id), func.min(MarketBand.day), func.max(MarketBand.day),
               func.avg(MarketBand.p50), func.max(MarketBand.updated_at))
        .where(MarketBand.day >= today)
        .group_by(MarketBand.city, MarketBand.bedrooms, MarketBand.source)
        .order_by(MarketBand.city, MarketBand.bedrooms)
    )
    out = []
    for city, bedrooms, source, days, d_from, d_to, p50, updated in (await session.execute(q)).all():
        out.append({
            "city": city, "bedrooms": bedrooms, "source": source, "days": days,
            "from": d_from.isoformat(), "to": d_to.isoformat(),
            "p50_avg": round(float(p50)) if p50 is not None else None,
            "updated_at": updated.isoformat() if updated else None,
        })
    return out
