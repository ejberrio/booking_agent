"""Feature 041: percentiles de mercado desde la Customer API de PriceLabs (solo lectura)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app.market import pricelabs as pl
from app.models.market import MarketBand, MarketFeed
from app.services import market_band_service, market_feed_service

pytestmark = pytest.mark.anyio

TODAY = date.today()
DAYS = [(TODAY + timedelta(days=i)).isoformat() for i in range(-1, 4)]
LABELS = ["25th Percentile", "50th Percentile", "75th Percentile", "Median Booked Price", "90th Percentile"]


def _block(n=40, base=200000):
    return {"Listings Used": n, "Active Used": n, "Inactive Used": 0, "X_values": DAYS,
            "Y_values": [[base * 0.7] * 5, [base] * 5, [base * 1.3] * 5, [base * 0.8] * 5,
                         [base * 1.6 + i for i in range(5)]]}


def _payload(categories):
    return {"data": {"Listings Used": 257, "currency": "COP",
                     "Neighborhood Data Source": "Market Dashboard: Mayorca Sabaneta",
                     "Future Percentile Prices": {"Category": categories, "Labels": LABELS}},
            "status": "Success"}


class FakePL:
    def __init__(self, status=200, body=None):
        self.status, self.body, self.calls = status, body, []

    def handler(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path, dict(req.url.params), req.headers.get("x-api-key")))
        if req.url.path == "/v1/listings":
            return httpx.Response(200, json={"listings": [
                {"id": "123", "pms": "beds24", "name": "Apto Mayorca", "city_name": "Sabaneta",
                 "no_of_bedrooms": 3, "push_enabled": False, "base": 250000}]})
        return httpx.Response(self.status, json=self.body)

    def client(self):
        return pl.PriceLabsClient("clave-de-prueba", transport=httpx.MockTransport(self.handler))


def test_lee_percentiles_por_tamano_o_compset():
    nb = pl.parse_neighborhood(_payload({"2": _block(), "3": _block(base=250000)})["data"], 3)
    assert nb.category == "3" and nb.source.startswith("Market Dashboard")
    assert nb.rows[1] == [DAYS[1], 175000.0, 250000.0, 325000.0, 400001.0]
    # compset del Market Dashboard: una sola categoría con su nombre
    nb = pl.parse_neighborhood(_payload({"ABB: 3 Bedrooms": _block()})["data"], 3)
    assert nb.category == "ABB: 3 Bedrooms" and len(nb.rows) == 5
    with pytest.raises(pl.PriceLabsError, match="categorías disponibles: 1, 2"):
        pl.parse_neighborhood(_payload({"1": _block(), "2": _block()})["data"], 3)


async def test_importa_desde_hoy_solo_lectura_y_sin_exponer_la_clave(session):
    fake = FakePL(body=_payload({"3": _block(base=250000)}))
    feed = await market_feed_service.save_feed(session, city="Sabaneta", bedrooms=3,
                                               listing_id="123", pms="beds24")
    client = fake.client()
    r = await market_feed_service.run_feed(session, feed, client, TODAY)
    await client.aclose()
    assert r["ok"] and r["imported"] == 4 and feed.city == "medellin"
    assert all(c[0] == "GET" for c in fake.calls)  # nunca escribe en PriceLabs
    assert fake.calls[0][2] == {"listing_id": "123", "pms": "beds24"}
    assert fake.calls[0][3] == "clave-de-prueba"
    assert "clave-de-prueba" not in (feed.last_status or "")
    bands = (await session.execute(select(MarketBand))).scalars().all()
    assert {b.source for b in bands} == {"pricelabs-api"} and len(bands) == 4
    assert {b.p90 for b in bands if b.day == TODAY} == {Decimal("400001")}
    caps = await market_band_service.caps_for(session, "Envigado", 3, TODAY, TODAY + timedelta(days=3))
    assert len(caps) == 4


async def test_errores_legibles_y_corrida_diaria(session):
    feed = await market_feed_service.save_feed(session, city="Medellín", bedrooms=3,
                                               listing_id="123", pms="beds24")
    fake = FakePL(status=400, body={"error": "Sync is off for this listing", "status": "Error"})
    notes = await market_feed_service.refresh_all(session, client_factory=fake.client, today=TODAY)
    assert "Sync Prices" in feed.last_status and feed.last_imported == 0
    assert notes and "medellin/3" in notes[0]
    assert (await session.execute(select(MarketBand))).first() is None

    # sin clave: la corrida diaria no falla y lo dice
    def no_key():
        return pl.PriceLabsClient(None)

    pl_get = pl.secret_service.get_secret
    try:
        pl.secret_service.get_secret = lambda *a, **k: None
        assert "Falta la clave" in (await market_feed_service.refresh_all(session, client_factory=no_key))[0]
    finally:
        pl.secret_service.get_secret = pl_get

    feed.enabled = False
    assert await market_feed_service.refresh_all(session, client_factory=fake.client) == []
    with pytest.raises(ValueError):
        await market_feed_service.save_feed(session, city="Ciudad Gótica", bedrooms=3,
                                            listing_id="1", pms="x")
    await market_feed_service.delete_feed(session, feed.id)
    assert (await session.execute(select(MarketFeed))).first() is None


async def test_lista_anuncios_sin_datos_de_mas():
    fake = FakePL()
    c = fake.client()
    out = await c.listings()
    await c.aclose()
    assert out == [{"id": "123", "pms": "beds24", "name": "Apto Mayorca", "city": "Sabaneta",
                    "bedrooms": 3, "sync": False}]


async def test_clave_invalida_403_de_cloudflare_se_explica():
    fake = FakePL(status=403, body={"error": {"code": "API_KEY_INVALID", "message": "An invalid api_key"}})
    c = fake.client()
    with pytest.raises(pl.PriceLabsError, match="rechazó la clave"):
        await c.neighborhood("123", "beds24", 3)
    await c.aclose()
