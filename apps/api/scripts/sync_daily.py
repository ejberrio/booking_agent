"""Sincronización diaria para cron.

Ejecuta import + reconcile (entrante) y deja registro en SyncRun. Requiere
credenciales en env y Postgres con migraciones aplicadas.

Uso (crontab):
    0 6 * * *  cd /ruta/apps/api && uv run python -m scripts.sync_daily
"""

import asyncio
from datetime import date, timedelta

from app.channels.beds24 import Beds24Adapter
from app.core.config import settings
from app.db.session import SessionLocal
from app.services import sync_service

HORIZON_DAYS = 365


async def main() -> None:
    adapter = Beds24Adapter(
        api_key=settings.beds24_api_key,
        prop_id=settings.beds24_prop_id,
        room_id=settings.beds24_room_id,
        base_url=settings.beds24_base_url,
    )
    try:
        async with SessionLocal() as session:
            today = date.today()
            run = await sync_service.import_remote(
                session, adapter, today, today + timedelta(days=HORIZON_DAYS)
            )
            await session.commit()
            print(
                f"sync_daily: run #{run.id} {run.status.value} "
                f"creados={run.created_count} incidencias={run.issue_count}"
            )
    finally:
        await adapter.aclose()


if __name__ == "__main__":
    asyncio.run(main())
