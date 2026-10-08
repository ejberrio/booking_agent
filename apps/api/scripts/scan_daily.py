"""Corrida diaria para cron: sincroniza con Beds24 y escanea inteligencia
(eventos + mercado → sugerencias).

La sincronización trae reservas/cancelaciones y, además, mantiene vivo el refresh
token de Beds24 (vence si pasa 30 días sin usarse).

Uso (crontab):
    0 5 * * *  cd /ruta/apps/api && uv run python -m scripts.scan_daily
"""

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.client import default_llm
from app.models.property import UnitType
from app.search.tavily import TavilyProvider
from app.services import intelligence_service

HORIZON_DAYS = 180
SYNC_DAYS = 365


async def _sync_channel() -> None:
    """Import entrante desde Beds24. Resiliente: si falla, el escaneo sigue."""
    from app.api.routes.sync import get_adapter
    from app.services import sync_service

    adapter = get_adapter()
    try:
        async with SessionLocal() as session:
            today = date.today()
            run = await sync_service.import_remote(
                session, adapter, today, today + timedelta(days=SYNC_DAYS)
            )
            await session.commit()
            print(
                f"scan_daily: sync #{run.id} {run.status.value} creadas={run.created_count} "
                f"actualizadas={run.updated_count} incidencias={run.issue_count}"
            )
    except Exception as exc:  # solo el tipo: nunca mensajes que puedan llevar secretos
        print(f"scan_daily: sync con Beds24 falló ({type(exc).__name__}); se continúa.")
    finally:
        await adapter.aclose()


async def main() -> None:
    # Secretos: BD cifrada > entorno (feature 017). Resiliente: si falla, entorno.
    try:
        from app.services import secret_service

        async with SessionLocal() as session:
            await secret_service.load_cache(session)
    except Exception:
        print("scan_daily: sin caché de secretos; se usan variables de entorno.")

    await _sync_channel()

    search = TavilyProvider()
    llm = default_llm()
    try:
        async with SessionLocal() as session:
            unit = (await session.execute(select(UnitType))).scalars().first()
            if unit is None:
                print("scan_daily: no hay unidades; nada que hacer.")
                return
            today = date.today()
            from app.market.tavily_market import TavilyMarketProvider

            market = TavilyMarketProvider(search, llm, session=session) if llm else None
            run = await intelligence_service.scan(
                session,
                search,
                llm,
                market,
                unit_type_id=unit.id,
                date_from=today,
                date_to=today + timedelta(days=HORIZON_DAYS),
            )
            await session.commit()
            print(
                f"scan_daily: run #{run.id} {run.status.value} "
                f"eventos={run.events_found} sugerencias={run.suggestions_created}"
            )
    finally:
        await search.aclose()


if __name__ == "__main__":
    asyncio.run(main())
