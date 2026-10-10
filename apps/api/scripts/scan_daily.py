"""Corrida diaria para cron: por CADA cuenta activa, sincroniza con Beds24 y escanea
inteligencia (eventos + mercado → sugerencias). Feature 026: multicliente.

- Cada cuenta corre en su propia sesión con su contexto (principio VI) y dentro de un
  try/except: el fallo de una cuenta queda registrado en ella y no detiene a las demás.
- Los eventos son datos públicos de una ciudad: las consultas generales de una ciudad se
  hacen UNA vez por corrida aunque varias cuentas estén en ella.
- La sincronización mantiene vivo el refresh token de Beds24 (vence a 30 días sin uso).

Uso (crontab):
    0 5 * * *  cd /ruta/apps/api && uv run python -m scripts.scan_daily
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import get_adapter, has_credentials
from app.db.tenancy import platform_session, tenant_session
from app.llm.client import default_llm
from app.models.account import Account, AccountStatus
from app.models.enums import SyncStatus
from app.models.intelligence import IntelligenceRun
from app.models.mixins import _now
from app.models.property import UnitType
from app.search.tavily import TavilyProvider
from app.services import event_service, intelligence_service, push_service, sync_service

HORIZON_DAYS = 180
SYNC_DAYS = 730  # 2 años: la app ve todo el horizonte cargado en Beds24 (feature 023)


async def active_account_ids(session: AsyncSession) -> list[int]:
    """Cuentas activas (sesión de plataforma: única consulta entre cuentas del cron)."""
    rows = await session.execute(
        select(Account.id).where(Account.status == AccountStatus.active).order_by(Account.id)
    )
    return list(rows.scalars())


async def sync_account(session: AsyncSession, today: date) -> str:
    """Import entrante desde el channel manager de la cuenta. Resiliente."""
    adapter = get_adapter(session)
    try:
        events: list = []
        run = await sync_service.import_remote(
            session, adapter, today, today + timedelta(days=SYNC_DAYS), events=events
        )
        # Avisos al celular de reservas que el webhook no informó (feature 025).
        await push_service.notify_booking_events(session, events)
        await session.commit()
        return (
            f"sync #{run.id} {run.status.value} creadas={run.created_count} "
            f"actualizadas={run.updated_count} incidencias={run.issue_count}"
        )
    except Exception as exc:  # solo el tipo: nunca mensajes que puedan llevar secretos
        await session.rollback()
        return f"sync falló ({type(exc).__name__}); se continúa"
    finally:
        await adapter.aclose()


async def scan_account(
    session: AsyncSession,
    *,
    search,
    llm,
    scanned_cities: set[str],
    today: date,
    market_factory=None,
) -> str:
    """Eventos + sugerencias de todas las unidades de la cuenta del contexto."""
    units = list((await session.execute(select(UnitType).order_by(UnitType.id))).scalars())
    if not units:
        return "sin unidades"
    city_key = event_service.normalize_city(await intelligence_service.property_city(session))
    include_city = city_key not in scanned_cities
    market = market_factory(session) if market_factory else None
    total = 0
    events_found = 0
    for i, unit in enumerate(units):
        run = await intelligence_service.scan(
            session,
            search,
            llm,
            market,
            unit_type_id=unit.id,
            date_from=today,
            date_to=today + timedelta(days=HORIZON_DAYS),
            # Solo la primera unidad busca eventos; las demás reutilizan los de la ciudad.
            queries=None if i == 0 else [],
            include_city_queries=include_city,
        )
        total += run.suggestions_created
        events_found += run.events_found
        await push_service.notify_suggestions(session, run.id, run.suggestions_created)
    scanned_cities.add(city_key)
    await session.commit()
    return f"{city_key}: eventos={events_found} sugerencias={total}"


async def _record_failure(account_id: int, exc: Exception) -> None:
    """Deja constancia del fallo EN la cuenta (sin mensajes crudos)."""
    try:
        async with tenant_session(account_id) as session:
            session.add(
                IntelligenceRun(
                    status=SyncStatus.failed,
                    finished_at=_now(),
                    detail=f"escaneo falló ({type(exc).__name__})",
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        pass


async def run_all(today: date | None = None, *, search=None, llm=None, market_factory=None) -> None:
    today = today or date.today()
    async with platform_session() as session:
        account_ids = await active_account_ids(session)
    scanned_cities: set[str] = set()
    for account_id in account_ids:
        try:
            async with tenant_session(account_id) as session:
                if not has_credentials(session):
                    print(f"scan_daily: cuenta {account_id} sin channel manager; se omite.")
                    continue
                print(f"scan_daily: cuenta {account_id} {await sync_account(session, today)}")
                summary = await scan_account(
                    session,
                    search=search,
                    llm=llm,
                    scanned_cities=scanned_cities,
                    today=today,
                    market_factory=market_factory,
                )
                print(f"scan_daily: cuenta {account_id} {summary}")
        except Exception as exc:  # noqa: BLE001 — el fallo de una cuenta no detiene a las demás
            print(f"scan_daily: cuenta {account_id} falló ({type(exc).__name__}); se continúa.")
            await _record_failure(account_id, exc)


async def main() -> None:
    # Secretos: BD cifrada > entorno (feature 017). Resiliente: si falla, entorno.
    try:
        from app.db.session import SessionLocal
        from app.services import secret_service

        async with SessionLocal() as session:
            await secret_service.load_cache(session)
    except Exception:
        print("scan_daily: sin caché de secretos; se usan variables de entorno.")

    search = TavilyProvider()
    llm = default_llm()

    def market_factory(session: AsyncSession):
        from app.market.tavily_market import TavilyMarketProvider

        return TavilyMarketProvider(search, llm, session=session) if llm else None

    try:
        await run_all(search=search, llm=llm, market_factory=market_factory)
    finally:
        await search.aclose()


if __name__ == "__main__":
    asyncio.run(main())
