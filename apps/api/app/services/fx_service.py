"""Tasas de cambio a pesos (feature 042): TRM oficial del Banco de la República.

Fuente: datos abiertos (datos.gov.co, conjunto 32sa-8pi3), sin clave. Solo se consulta desde la
corrida diaria; los informes leen lo guardado en `fx_rate` y nunca llaman a la red.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.finance import FxRate

TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
LOOKBACK_DAYS = 10  # fines de semana y festivos usan la última TRM vigente


async def rate_for(session: AsyncSession, currency: str, day: date, quote: str = "COP") -> Decimal | None:
    """TRM vigente ese día (o la última de los 10 días anteriores). Misma moneda → 1."""
    if not currency or currency == quote:
        return Decimal(1)
    row = (
        await session.execute(
            select(FxRate.rate)
            .where(FxRate.currency == currency, FxRate.quote == quote,
                   FxRate.day <= day, FxRate.day >= day - timedelta(days=LOOKBACK_DAYS))
            .order_by(FxRate.day.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row


async def latest(session: AsyncSession, currency: str, quote: str = "COP") -> Decimal | None:
    if currency == quote:
        return Decimal(1)
    return (
        await session.execute(
            select(FxRate.rate).where(FxRate.currency == currency, FxRate.quote == quote)
            .order_by(FxRate.day.desc()).limit(1)
        )
    ).scalar_one_or_none()


async def _fetch_trm(client: httpx.AsyncClient, date_from: date, date_to: date) -> dict[date, Decimal]:
    """TRM USD→COP por día del rango (cada registro cubre un tramo vigencia desde–hasta)."""
    where = (f"vigenciahasta >= '{date_from.isoformat()}T00:00:00' AND "
             f"vigenciadesde <= '{date_to.isoformat()}T00:00:00'")
    resp = await client.get(TRM_URL, params={"$where": where, "$limit": 2000})
    resp.raise_for_status()
    out: dict[date, Decimal] = {}
    for r in resp.json():
        try:
            start = date.fromisoformat(r["vigenciadesde"][:10])
            end = date.fromisoformat(r["vigenciahasta"][:10])
            value = Decimal(str(r["valor"]))
        except (KeyError, ValueError, ArithmeticError):
            continue
        d = max(start, date_from)
        while d <= min(end, date_to):
            out[d] = value
            d += timedelta(days=1)
    return out


async def refresh_for_bookings(session: AsyncSession, today: date | None = None,
                               client: httpx.AsyncClient | None = None) -> int:
    """Guarda la TRM de los días de llegada de las reservas en USD que aún no la tienen.
    Una sola consulta por corrida. Devuelve cuántos días nuevos se guardaron."""
    today = today or date.today()
    days = {
        d for (d,) in (
            await session.execute(
                select(Booking.check_in).where(Booking.currency == "USD", Booking.amount.is_not(None))
            )
        ).all()
    }
    days.add(today)
    days = {min(d, today) for d in days}
    have = {
        d for (d,) in (
            await session.execute(
                select(FxRate.day).where(FxRate.currency == "USD", FxRate.quote == "COP",
                                         FxRate.day >= min(days) - timedelta(days=LOOKBACK_DAYS))
            )
        ).all()
    }
    missing = sorted(d for d in days if d not in have)
    if not missing:
        return 0
    own = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        rates = await _fetch_trm(client, missing[0] - timedelta(days=LOOKBACK_DAYS), missing[-1])
    finally:
        if own:
            await client.aclose()
    n = 0
    for d, value in sorted(rates.items()):
        if d in have:
            continue
        session.add(FxRate(currency="USD", quote="COP", day=d, rate=value, source="trm"))
        have.add(d)
        n += 1
    await session.flush()
    return n
