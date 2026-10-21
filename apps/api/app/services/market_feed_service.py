"""Carga automática de percentiles de mercado desde la API de PriceLabs (feature 041).

Cada `MarketFeed` une una zona y un tamaño con un anuncio de la cuenta de PriceLabs de la
plataforma. La corrida diaria (scan_daily) lee su `neighborhood_data` y llena `market_band`
con los mismos percentiles que el CSV de "Precios Futuros" (feature 040), que queda de
respaldo. Datos agregados de plataforma; nada se escribe en PriceLabs.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import municipalities
from app.market.pricelabs import PriceLabsClient, PriceLabsError
from app.models.market import MarketFeed
from app.services import market_band_service

SOURCE = "pricelabs-api"


def _out(f: MarketFeed) -> dict:
    return {
        "id": f.id, "city": f.city, "bedrooms": f.bedrooms, "listing_id": f.listing_id,
        "pms": f.pms, "enabled": f.enabled,
        "last_run_at": f.last_run_at.isoformat() if f.last_run_at else None,
        "last_status": f.last_status, "last_imported": f.last_imported,
    }


async def list_feeds(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(MarketFeed).order_by(MarketFeed.city, MarketFeed.bedrooms)))
    return [_out(f) for f in rows.scalars()]


async def save_feed(session: AsyncSession, *, city: str, bedrooms: int, listing_id: str,
                    pms: str, enabled: bool = True) -> MarketFeed:
    """Crea o reemplaza la configuración de una zona y tamaño."""
    key = municipalities.area_core_key(city)
    if municipalities.by_city_key(key) is None:
        raise ValueError(f'No reconozco el municipio "{city}".')
    feed = (await session.execute(
        select(MarketFeed).where(MarketFeed.city == key, MarketFeed.bedrooms == bedrooms)
    )).scalar_one_or_none()
    if feed is None:
        feed = MarketFeed(city=key, bedrooms=bedrooms)
        session.add(feed)
    feed.listing_id, feed.pms, feed.enabled = listing_id.strip(), pms.strip(), enabled
    await session.flush()
    return feed


async def delete_feed(session: AsyncSession, feed_id: int) -> None:
    feed = await session.get(MarketFeed, feed_id)
    if feed is None:
        raise LookupError("No existe esa configuración")
    await session.delete(feed)
    await session.flush()


async def run_feed(session: AsyncSession, feed: MarketFeed, client: PriceLabsClient,
                   today: date | None = None) -> dict:
    """Lee el vecindario del anuncio e importa los percentiles desde hoy. Nunca lanza: el
    resultado (o el error legible) queda en la configuración."""
    today = today or date.today()
    feed.last_run_at = datetime.now(UTC)
    try:
        nb = await client.neighborhood(feed.listing_id, feed.pms, feed.bedrooms)
        rows = [r for r in nb.rows if r[0] >= today.isoformat()]
        if not rows:
            raise PriceLabsError("PriceLabs no trajo fechas futuras con los cuatro percentiles.")
        n = await market_band_service.import_rows(
            session, city=feed.city, bedrooms=feed.bedrooms, rows=rows, source=SOURCE
        )
        feed.last_imported = n
        feed.last_status = (f"ok: {n} fechas ({rows[0][0]} a {rows[-1][0]}) · "
                            f"{nb.source or 'origen ?'} · categoría {nb.category}")[:200]
        result = {"ok": True, "imported": n, "source": nb.source, "category": nb.category,
                  "categories": nb.categories, "currency": nb.currency,
                  "from": rows[0][0], "to": rows[-1][0]}
    except PriceLabsError as exc:
        feed.last_imported = 0
        feed.last_status = f"error: {exc}"[:200]
        result = {"ok": False, "error": str(exc)}
    await session.flush()
    return result


async def refresh_all(session: AsyncSession, *,
                      client_factory: Callable[[], PriceLabsClient] = PriceLabsClient,
                      today: date | None = None) -> list[str]:
    """Corrida diaria: todas las configuraciones activas. Sin clave → no hace nada."""
    feeds = list((await session.execute(
        select(MarketFeed).where(MarketFeed.enabled.is_(True)).order_by(MarketFeed.id)
    )).scalars())
    if not feeds:
        return []
    try:
        client = client_factory()
    except PriceLabsError as exc:
        return [str(exc)]
    notes = []
    try:
        for feed in feeds:
            r = await run_feed(session, feed, client, today)
            notes.append(f"{feed.city}/{feed.bedrooms}: {feed.last_status}")
            if not r["ok"] and "rechazó la clave" in r["error"]:
                break  # clave inválida: no tiene sentido seguir gastando consultas
    finally:
        await client.aclose()
    return notes
