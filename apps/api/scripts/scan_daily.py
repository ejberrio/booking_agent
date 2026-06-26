"""Escaneo diario de inteligencia (eventos + mercado → sugerencias) para cron.

Uso (crontab):
    0 5 * * *  cd /ruta/apps/api && uv run python -m scripts.scan_daily
"""

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.client import default_llm
from app.market.reference import BaselineMarket
from app.models.property import UnitType
from app.search.tavily import TavilyProvider
from app.services import intelligence_service

QUERIES = [
    "eventos en Medellín este mes conciertos ferias convenciones",
    "festivales y eventos importantes Medellín próximos meses",
]
HORIZON_DAYS = 180


async def main() -> None:
    search = TavilyProvider()
    llm = default_llm()
    try:
        async with SessionLocal() as session:
            unit = (await session.execute(select(UnitType))).scalars().first()
            if unit is None:
                print("scan_daily: no hay unidades; nada que hacer.")
                return
            today = date.today()
            run = await intelligence_service.scan(
                session,
                search,
                llm,
                BaselineMarket(session),
                queries=QUERIES,
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
