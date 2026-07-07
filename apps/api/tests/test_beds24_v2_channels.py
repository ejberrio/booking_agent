"""Feature 012: mapeo del canal de origen de reservas en los adaptadores Beds24.

Verifica que `RemoteBooking.channel` sale como token neutro desde el campo
`channel` de V2 (fallback `referer`) y que un origen desconocido produce None
sin romper el lote. Dobles con httpx.MockTransport, sin API real.
"""

from __future__ import annotations

import httpx
import pytest

from app.channels.base import infer_channel_token
from app.channels.beds24_v2 import Beds24V2Adapter

pytestmark = pytest.mark.anyio


def adapter_with(handler) -> Beds24V2Adapter:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.beds24.com/v2")
    return Beds24V2Adapter(refresh_token="refresh-xyz", client=client, retry_base_delay=0)


def _token_ok(request: httpx.Request) -> httpx.Response | None:
    if request.url.path.endswith("/authentication/token"):
        return httpx.Response(200, json={"token": "tok-123", "expiresIn": 86400})
    return None


def _booking(bid: int, **extra) -> dict:
    return {
        "id": bid,
        "roomId": 697411,
        "arrival": "2026-08-06",
        "departure": "2026-08-19",
        "status": "confirmed",
        **extra,
    }


async def test_get_bookings_maps_channel_tokens():
    """channel explícito, fallback por referer, y origen ausente → None."""

    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    _booking(1, channel="booking", referer="Booking.com"),
                    _booking(2, channel="airbnb"),
                    _booking(3, referer="Airbnb"),  # sin channel: infiere del referer
                    _booking(4),  # reserva manual: sin origen
                    _booking(5, channel="", referer="Walk-In Front Desk"),  # irreconocible
                ],
            },
        )

    adapter = adapter_with(handler)
    try:
        bookings = await adapter.get_bookings("337229")
    finally:
        await adapter.aclose()

    by_id = {b.external_id: b.channel for b in bookings}
    assert by_id == {"1": "booking", "2": "airbnb", "3": "airbnb", "4": None, "5": None}
    # El lote completo se importa aunque haya orígenes desconocidos.
    assert len(bookings) == 5


async def test_get_bookings_channel_is_normalized_lowercase():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(
            200,
            json={"success": True, "data": [_booking(9, channel="  Booking  ")]},
        )

    adapter = adapter_with(handler)
    try:
        bookings = await adapter.get_bookings("337229")
    finally:
        await adapter.aclose()
    assert bookings[0].channel == "booking"


def test_infer_channel_token_rules():
    """Helper compartido V1/V2: prioridad channel > referer; nunca lanza."""
    assert infer_channel_token("booking", None) == "booking"
    assert infer_channel_token("AIRBNB", "Booking.com") == "airbnb"  # channel manda
    assert infer_channel_token(None, "Booking.com") == "booking"
    assert infer_channel_token(None, "Airbnb (API)") == "airbnb"
    assert infer_channel_token(None, "Teléfono") is None
    assert infer_channel_token("", "") is None
    assert infer_channel_token(None, None) is None
    assert infer_channel_token(123, None) == "123"  # tipos raros no rompen


async def test_get_bookings_composes_guest_name():
    """firstName+lastName → compuesto; parciales OK; ausentes → None (feature 016)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    _booking(1, firstName="John", lastName="Doe"),
                    _booking(2, firstName="Ana"),
                    _booking(3, lastName="Roe"),
                    _booking(4),
                    _booking(5, firstName="", lastName=""),
                ],
            },
        )

    adapter = adapter_with(handler)
    try:
        names = {b.external_id: b.guest_name for b in await adapter.get_bookings("337229")}
    finally:
        await adapter.aclose()
    assert names == {"1": "John Doe", "2": "Ana", "3": "Roe", "4": None, "5": None}


async def test_get_bookings_pide_tambien_canceladas():
    """Issue #91: el default de V2 excluye 'cancelled' — hay que pedirlo explícito."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        seen["status"] = request.url.params.get_list("status")
        return httpx.Response(200, json={"success": True, "data": [
            _booking(1, status="cancelled", channel="booking"),
        ]})

    adapter = adapter_with(handler)
    try:
        bookings = await adapter.get_bookings("337229")
    finally:
        await adapter.aclose()
    assert "cancelled" in seen["status"] and "confirmed" in seen["status"]
    assert bookings[0].status == "cancelled"
