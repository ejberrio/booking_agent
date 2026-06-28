"""Pruebas del adaptador Beds24 V2 con httpx.MockTransport (sin API real)."""

from datetime import date
from decimal import Decimal as D

import httpx
import pytest

from app.channels.beds24_v2 import Beds24V2Adapter
from app.channels.errors import AuthError

pytestmark = pytest.mark.anyio

DAY = date(2026, 7, 15)


def adapter_with(handler, **kw) -> Beds24V2Adapter:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.beds24.com/v2")
    return Beds24V2Adapter(refresh_token="refresh-xyz", client=client, retry_base_delay=0, **kw)


def _token_ok(request: httpx.Request) -> httpx.Response | None:
    """Responde el endpoint de token; None si no es esa ruta."""
    if request.url.path.endswith("/authentication/token"):
        assert request.headers.get("refreshToken") == "refresh-xyz"
        return httpx.Response(200, json={"token": "tok-123", "expiresIn": 86400})
    return None


async def test_get_properties_maps():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        assert request.headers.get("token") == "tok-123"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {
                        "id": 337229,
                        "name": "Apartamento con piscina",
                        "currency": "COP",
                        "roomTypes": [{"id": 697411, "name": "Three-Bedroom", "qty": 1}],
                    }
                ],
            },
        )

    adapter = adapter_with(handler)
    props = await adapter.get_properties()
    assert props[0].external_id == "337229"
    assert props[0].rooms[0].external_id == "697411"
    assert props[0].rooms[0].units_count == 1
    await adapter.aclose()


async def test_get_rates_expands_ranges():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {
                        "roomId": 697411,
                        "calendar": [
                            {"from": "2026-07-15", "to": "2026-07-17", "numAvail": 1, "price1": 350000}
                        ],
                    }
                ],
            },
        )

    adapter = adapter_with(handler)
    rates = await adapter.get_rates("697411", DAY, date(2026, 7, 17))
    assert len(rates) == 3  # rango expandido a días
    assert all(r.price == D("350000") for r in rates)
    assert rates[0].available == 1
    await adapter.aclose()


async def test_get_bookings_maps():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {
                        "id": 88836150,
                        "roomId": 697411,
                        "arrival": "2026-08-06",
                        "departure": "2026-08-19",
                        "status": "new",
                    }
                ],
            },
        )

    adapter = adapter_with(handler)
    bks = await adapter.get_bookings("337229")
    assert bks[0].external_id == "88836150"
    assert bks[0].check_in == date(2026, 8, 6)
    assert bks[0].check_out == date(2026, 8, 19)  # departure directo
    assert bks[0].status == "confirmed"
    await adapter.aclose()


async def test_set_rate_verifies():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        if request.method == "POST":
            return httpx.Response(
                200,
                json=[{"success": True, "modified": {"roomId": 697411}}],
            )
        # relectura confirma el precio
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {"roomId": 697411, "calendar": [{"from": "2026-07-15", "to": "2026-07-15", "price1": 415800}]}
                ],
            },
        )

    adapter = adapter_with(handler)
    res = await adapter.set_rate("697411", DAY, D("415800"))
    assert res.ok is True and res.verified is True
    await adapter.aclose()


async def test_set_rate_unverified_when_reread_differs():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        if request.method == "POST":
            return httpx.Response(200, json=[{"success": True}])
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {"roomId": 697411, "calendar": [{"from": "2026-07-15", "to": "2026-07-15", "price1": 350000}]}
                ],
            },
        )

    adapter = adapter_with(handler)
    res = await adapter.set_rate("697411", DAY, D("415800"))
    assert res.verified is False
    await adapter.aclose()


async def test_auth_error_when_no_token():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/authentication/token"):
            return httpx.Response(401, json={"error": "invalid refreshToken"})
        return httpx.Response(200, json={"success": True, "data": []})

    adapter = adapter_with(handler)
    with pytest.raises(AuthError):
        await adapter.get_properties()
    await adapter.aclose()


async def test_secret_not_leaked_in_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(200, json={"success": False, "error": "boom with refresh-xyz"})

    adapter = adapter_with(handler)
    with pytest.raises(Exception) as ei:
        await adapter.get_properties()
    assert "refresh-xyz" not in str(ei.value)
    await adapter.aclose()


async def test_set_availability_verifies():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        if request.method == "POST":
            return httpx.Response(200, json=[{"success": True, "modified": {"roomId": 697411}}])
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {"roomId": 697411, "calendar": [{"from": "2026-07-15", "to": "2026-07-15", "numAvail": 0, "price1": 350000}]}
                ],
            },
        )

    adapter = adapter_with(handler)
    res = await adapter.set_availability_range("697411", DAY, DAY, 0)
    assert res.ok is True and res.verified is True
    await adapter.aclose()
