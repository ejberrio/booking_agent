"""Feature 026: el escaneo diario recorre cada cuenta, una ciudad se busca una sola vez y el
fallo de una cuenta no detiene a las demás."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.channels.base import RemoteProperty, RemoteRate, RemoteRoom
from app.channels.errors import AuthError
from app.db.tenancy import mark_platform, set_tenant
from app.llm.client import LLMResponse
from app.models.account import Account
from app.models.intelligence import IntelligenceRun
from app.models.enums import SyncStatus
from app.models.market import Event
from app.models.property import Property
from app.search.base import SearchResult
from scripts import scan_daily

pytestmark = pytest.mark.anyio

TODAY = date.today()


class CM:
    def __init__(self, prop_ref: str, city: str, *, broken: bool = False):
        self.prop_ref, self.city, self.broken = prop_ref, city, broken

    async def get_properties(self):
        if self.broken:
            raise AuthError("token vencido")
        return [RemoteProperty(self.prop_ref, f"Casa {self.city}", "COP",
                               [RemoteRoom(f"{self.prop_ref}-r", "3BR", 1)])]

    async def get_rates(self, room, df, dt):
        out, d = [], df
        while d <= dt:
            out.append(RemoteRate(room, d, Decimal("300000"), 1))
            d += timedelta(days=1)
        return out

    async def get_bookings(self, prop, since=None):
        return []

    async def aclose(self):
        return None


class Search:
    def __init__(self):
        self.queries: list[str] = []

    async def search(self, query, *, max_results=5):
        self.queries.append(query)
        return [SearchResult(title="Agenda", url="https://x.co", content=query)]


class LLM:
    async def chat(self, *, messages, tools, model):
        day = (TODAY + timedelta(days=20)).isoformat()
        city = "Cartagena" if "Cartagena" in messages[0]["content"] else "Medellín"
        return LLMResponse(
            content=f'[{{"name":"Festival {city}","start_date":"{day}","end_date":null,'
            f'"kind":"festival","relevance":"high","location":"{city}"}}]'
        )


async def test_recorre_cuentas_ciudad_una_vez_y_aisla_fallos(session, monkeypatch):
    maker = session.info["maker"]
    async with maker() as setup:
        mark_platform(setup)
        setup.add_all([Account(id=2, name="Medellín 2"), Account(id=3, name="Cartagena"),
                       Account(id=4, name="Rota")])
        await setup.commit()

    cms = {1: CM("100", "Medellín"), 2: CM("200", "Medellín"), 3: CM("300", "Cartagena"),
           4: CM("400", "Medellín", broken=True)}

    @asynccontextmanager
    async def fake_tenant(account_id, user_id=None):
        async with maker() as s:
            set_tenant(s, account_id, user_id)
            yield s

    @asynccontextmanager
    async def fake_platform():
        async with maker() as s:
            mark_platform(s)
            yield s

    monkeypatch.setattr(scan_daily, "tenant_session", fake_tenant)
    monkeypatch.setattr(scan_daily, "platform_session", fake_platform)
    monkeypatch.setattr(scan_daily, "has_credentials", lambda s: True)
    monkeypatch.setattr(
        scan_daily, "get_adapter", lambda s: cms[s.info["account_id"]]
    )

    # La ciudad de cada cuenta la da su propiedad (el import no trae ciudad: se fija aquí).
    real_sync = scan_daily.sync_account

    async def sync_and_city(s, today):
        out = await real_sync(s, today)
        acc = s.info["account_id"]
        for prop in (await s.execute(select(Property))).scalars():
            prop.city = cms[acc].city
        await s.commit()
        return out

    monkeypatch.setattr(scan_daily, "sync_account", sync_and_city)

    search = Search()
    await scan_daily.run_all(TODAY, search=search, llm=LLM())

    # Consultas generales: una vez por ciudad (Medellín y Cartagena), no por cuenta.
    general = [q for q in search.queries if q.startswith("eventos importantes agenda")]
    assert sorted(general) == ["eventos importantes agenda Cartagena",
                               "eventos importantes agenda Medellín"]

    async with maker() as plat:
        mark_platform(plat)
        cities = sorted({e.city for e in (await plat.execute(select(Event))).scalars()})
        assert cities == ["cartagena", "medellin"]
        runs = list((await plat.execute(select(IntelligenceRun))).scalars())
    by_acc = {r.account_id: r for r in runs}
    assert by_acc[1].status == SyncStatus.success and by_acc[3].status == SyncStatus.success
    # La cuenta rota: sync falló y no hay unidades → sin escaneo, sin afectar a las demás.
    assert 4 not in by_acc or by_acc[4].status != SyncStatus.success
