from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.channels.beds24 import Beds24Adapter
from app.channels.errors import AuthError, ChannelError, RateLimited

D = Decimal
DAY = date(2026, 7, 15)


def adapter_with(handler: Callable[[httpx.Request], httpx.Response], **kw) -> Beds24Adapter:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return Beds24Adapter(api_key=kw.pop("api_key", "k"), prop_id="337229", client=client,
                         retry_base_delay=0, **kw)


PROPS_JSON = {
    "getProperties": [
        {
            "propId": "337229",
            "name": "Apartamento con piscina",
            "currency": "COP",
            "roomTypes": [{"roomId": "697411", "name": "Three-Bedroom Apartment", "qty": "2"}],
        }
    ]
}


async def test_get_properties_maps_dtos():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/getProperties")
        return httpx.Response(200, json=PROPS_JSON)

    adapter = adapter_with(handler)
    props = await adapter.get_properties()
    assert props[0].external_id == "337229"
    assert props[0].currency == "COP"
    assert props[0].rooms[0].external_id == "697411"
    assert props[0].rooms[0].units_count == 2
    await adapter.aclose()


async def test_connection_ok():
    adapter = adapter_with(lambda r: httpx.Response(200, json=PROPS_JSON))
    info = await adapter.test_connection()
    assert info.ok is True
    assert info.properties[0].external_id == "337229"
    await adapter.aclose()


async def test_auth_error_hides_secret():
    secret = "supersecret-api-key-xyz"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Invalid API key / credential"})

    adapter = adapter_with(handler, api_key=secret)
    with pytest.raises(AuthError) as ei:
        await adapter.get_properties()
    assert secret not in str(ei.value)
    await adapter.aclose()


async def test_get_rates_maps():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"roomDates": [{"date": "2026-07-15", "price": 180000, "numAvail": 1}]}
        )

    adapter = adapter_with(handler)
    rates = await adapter.get_rates("697411", DAY, DAY)
    assert rates[0].price == D("180000")
    assert rates[0].available == 1
    await adapter.aclose()


async def test_get_bookings_maps():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "bookings": [
                    {
                        "bookId": 555,
                        "roomId": 697411,
                        "checkIn": "2026-07-15",
                        "checkOut": "2026-07-18",
                        "status": "confirmed",
                    }
                ]
            },
        )

    adapter = adapter_with(handler)
    bks = await adapter.get_bookings("337229")
    assert bks[0].external_id == "555"
    assert bks[0].check_in == DAY
    assert bks[0].check_out == date(2026, 7, 18)
    await adapter.aclose()


async def test_set_rate_verifies():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/setRoomDates"):
            return httpx.Response(200, json={"success": True})
        return httpx.Response(
            200, json={"roomDates": [{"date": "2026-07-15", "price": 200000, "numAvail": 1}]}
        )

    adapter = adapter_with(handler)
    res = await adapter.set_rate("697411", DAY, D("200000"))
    assert res.ok is True and res.verified is True
    await adapter.aclose()


async def test_set_rate_unverified():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/setRoomDates"):
            return httpx.Response(200, json={"success": True})
        # relectura devuelve un precio distinto -> no verificado
        return httpx.Response(
            200, json={"roomDates": [{"date": "2026-07-15", "price": 180000, "numAvail": 1}]}
        )

    adapter = adapter_with(handler)
    res = await adapter.set_rate("697411", DAY, D("200000"))
    assert res.verified is False
    await adapter.aclose()


async def test_rate_limit_retries_then_raises():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"error": "rate limit exceeded, too many requests"})

    adapter = adapter_with(handler, max_retries=3)
    with pytest.raises(RateLimited):
        await adapter.get_properties()
    assert calls["n"] == 3
    await adapter.aclose()


async def test_comm_error_raises_channel_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    adapter = adapter_with(handler, max_retries=2)
    with pytest.raises(ChannelError):
        await adapter.get_properties()
    await adapter.aclose()
