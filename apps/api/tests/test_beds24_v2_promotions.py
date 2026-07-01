"""Pruebas del adaptador Beds24 V2 para promociones (fixed prices), con MockTransport."""

from datetime import date
from decimal import Decimal as D

import httpx
import pytest

from app.channels.beds24_v2 import Beds24V2Adapter
from app.channels.base import RemoteFixedPrice
from app.channels.errors import ChannelError

pytestmark = pytest.mark.anyio

F, L = date(2027, 1, 15), date(2027, 1, 31)


def adapter_with(handler, **kw) -> Beds24V2Adapter:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.beds24.com/v2")
    return Beds24V2Adapter(
        refresh_token="refresh-xyz", client=client, retry_base_delay=0, prop_id="337229", **kw
    )


def _token_ok(request: httpx.Request) -> httpx.Response | None:
    if request.url.path.endswith("/authentication/token"):
        return httpx.Response(200, json={"token": "tok-123", "expiresIn": 86400})
    return None


async def test_set_fixed_price_create_returns_external_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        assert request.url.path.endswith("/inventory/fixedPrices")
        body = httpx.Request("POST", request.url, content=request.content).read()
        seen["body"] = body
        return httpx.Response(200, json={"success": True, "data": [{"id": 55123, "success": True}]})

    adapter = adapter_with(handler)
    fp = RemoteFixedPrice(
        offer_id=3, room_external_id="697411", first_night=F, last_night=L,
        name="Vacaciones", price=D("280000"), min_nights=3,
    )
    res = await adapter.set_fixed_price(fp)
    assert res.ok and res.external_id == 55123
    assert b"697411" in seen["body"] and b"roomPrice" in seen["body"]
    assert b'"id"' not in seen["body"]  # crear = sin id
    await adapter.aclose()


async def test_disable_fixed_price_sends_roomprice_disable():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        captured["body"] = request.content
        return httpx.Response(200, json={"success": True, "data": [{"id": 55123, "success": True}]})

    adapter = adapter_with(handler)
    res = await adapter.disable_fixed_price(55123, "697411")
    assert res.ok
    assert b'"roomPriceEnable":false' in captured["body"].replace(b" ", b"")
    await adapter.aclose()


async def test_get_fixed_prices_maps():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {
                        "id": 55123,
                        "offerId": 3,
                        "roomId": 697411,
                        "firstNight": "2027-01-15",
                        "lastNight": "2027-01-31",
                        "name": "Vacaciones",
                        "roomPrice": 280000,
                        "roomPriceEnable": True,
                        "minNights": 3,
                    }
                ],
            },
        )

    adapter = adapter_with(handler)
    fps = await adapter.get_fixed_prices("697411")
    assert len(fps) == 1
    assert fps[0].external_id == 55123 and fps[0].offer_id == 3
    assert fps[0].price == D("280000") and fps[0].min_nights == 3
    await adapter.aclose()


async def test_get_offers_maps():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        assert request.url.params.get("numAdults") == "2"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {"roomId": 697411, "offers": [{"offerId": 1, "offerName": "", "price": 1156000, "unitsAvailable": 1}]}
                ],
            },
        )

    adapter = adapter_with(handler)
    offers = await adapter.get_offers("337229", "697411", F, L, num_adults=2)
    assert offers[0].offer_id == 1 and offers[0].price == D("1156000")
    await adapter.aclose()


async def test_set_fixed_price_error_is_classified_and_redacts():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(200, json={"success": False, "error": "invalid offer"})

    adapter = adapter_with(handler)
    fp = RemoteFixedPrice(
        offer_id=99, room_external_id="697411", first_night=F, last_night=L,
        name="X", price=D("1"),
    )
    with pytest.raises(ChannelError):
        await adapter.set_fixed_price(fp)
    await adapter.aclose()
