"""Feature 018: POIs, configuración del scan, query builder y proveedor de mercado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio

from app.db.session import get_session
from app.llm.client import LLMResponse
from app.main import app
from app.market.tavily_market import TavilyMarketProvider
from app.models.intelligence import MarketReference
from app.models.market import PointOfInterest
from app.models.property import Property
from app.search.base import SearchResult
from app.services import intelligence_service
from sqlalchemy import select

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date(2026, 9, 1)


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_pois_crud_y_validaciones(client, session):
    res = await client.post(
        "/pois",
        json={
            "name": "Daviarena",
            "note": "muy cerca del apartamento",
            "date_from": "2026-09-01",
            "date_to": "2026-11-30",
        },
    )
    assert res.status_code == 200
    poi = res.json()

    assert (await client.post("/pois", json={"name": "  "})).status_code == 422
    assert (
        await client.post(
            "/pois", json={"name": "X", "date_from": "2026-11-30", "date_to": "2026-09-01"}
        )
    ).status_code == 422

    upd = await client.patch(f"/pois/{poi['id']}", json={"is_active": False})
    assert upd.json()["is_active"] is False
    assert (await client.delete(f"/pois/{poi['id']}")).json() == {"deleted": True}
    assert (await client.delete(f"/pois/{poi['id']}")).status_code == 404


async def test_scan_config_defaults_y_validacion(client, session):
    session.add(Property(name="Apto", city="Sabaneta", address="Cra 48 frente a Mayorca"))
    await session.flush()
    cfg = (await client.get("/scan-config")).json()
    assert cfg["queries_per_scan"] == 12
    assert cfg["zone"] is None
    assert "Sabaneta" in cfg["effective_zone"] and "Mayorca" in cfg["effective_zone"]

    assert (await client.put("/scan-config", json={"queries_per_scan": 99})).status_code == 422
    upd = (await client.put("/scan-config", json={"zone": "Sabaneta sur", "queries_per_scan": 5}))
    assert upd.json()["effective_zone"] == "Sabaneta sur"


async def test_query_builder_pois_y_presupuesto(session):
    session.add(Property(name="Apto", city="Sabaneta"))
    session.add(PointOfInterest(name="Daviarena", date_from=date(2026, 9, 1), date_to=date(2026, 11, 30)))
    session.add(PointOfInterest(name="Vencido", date_to=date(2026, 1, 1)))
    session.add(PointOfInterest(name="Inactivo", is_active=False))
    await session.flush()
    queries, detail = await intelligence_service.build_scan_queries(session, TODAY)
    joined = " | ".join(queries)
    assert "Daviarena" in joined
    assert "Vencido" not in joined and "Inactivo" not in joined
    assert detail["pois"] == ["Daviarena"]
    assert len(queries) <= detail["budget"]

    # presupuesto corto
    cfg = await intelligence_service.get_or_create_scan_config(session)
    cfg.queries_per_scan = 1
    await session.flush()
    queries2, detail2 = await intelligence_service.build_scan_queries(session, TODAY)
    assert len(queries2) == 1 and detail2["truncated"] is True


# --- proveedor de mercado gratis -------------------------------------------------


class FakeSearch:
    async def search(self, query, *, max_results=5):
        return [SearchResult("Tarifas", "Apartamentos en Sabaneta desde $280.000 la noche")]


class FakeLLM:
    def __init__(self, content):
        self.content = content

    async def chat(self, *, messages, tools, model):
        return LLMResponse(content=self.content)


async def test_market_provider_mediana_y_persistencia(session):
    provider = TavilyMarketProvider(FakeSearch(), FakeLLM("[280000, 310000, 350000]"), session=session)
    snap = await provider.get_snapshot("Sabaneta", date(2026, 9, 1))
    assert snap.adr == D("310000")  # mediana
    assert snap.sample_size == 3 and snap.low_confidence is False
    ref = (await session.execute(select(MarketReference))).scalar_one()
    assert ref.source == "tavily" and ref.sample_size == 3


async def test_market_provider_sin_datos_none(session):
    provider = TavilyMarketProvider(FakeSearch(), FakeLLM("[]"))
    assert await provider.get_snapshot("Sabaneta", date(2026, 9, 1)) is None
    # valores basura filtrados por cordura
    provider2 = TavilyMarketProvider(FakeSearch(), FakeLLM('[42, "texto", 99999999]'))
    assert await provider2.get_snapshot("Sabaneta", date(2026, 9, 1)) is None


async def test_market_provider_pocas_muestras_baja_confianza(session):
    provider = TavilyMarketProvider(FakeSearch(), FakeLLM("[280000, 320000]"))
    snap = await provider.get_snapshot("Sabaneta", date(2026, 9, 1))
    assert snap.sample_size == 2 and snap.low_confidence is True
