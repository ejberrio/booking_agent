"""Feature 013: ajuste de precio por canal y alcance de fixed prices en el
adaptador Beds24 V2 (contrato channel-manager-port.md, casos 1-6).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal as D

import httpx
import pytest

from app.channels.base import RemoteFixedPrice
from app.channels.beds24_v2 import Beds24V2Adapter

pytestmark = pytest.mark.anyio

PREFIX = "*[CONVERT:COP-USD]"


def adapter_with(handler) -> Beds24V2Adapter:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.beds24.com/v2")
    return Beds24V2Adapter(refresh_token="refresh-xyz", client=client, retry_base_delay=0)


def _token_ok(request: httpx.Request) -> httpx.Response | None:
    if request.url.path.endswith("/authentication/token"):
        return httpx.Response(200, json={"token": "tok-123", "expiresIn": 86400})
    return None


def _settings_payload(multiplier: str | None) -> dict:
    return {
        "success": True,
        "data": [
            {
                "channel": "airbnb",
                "properties": [
                    {"id": 337229, "multiplier": multiplier, "currency": "USD"}
                ],
            }
        ],
    }


# --- Caso 1: parseo ---------------------------------------------------------


def test_split_multiplier_cases():
    split = Beds24V2Adapter._split_multiplier
    assert split(f"{PREFIX}*1.08") == (PREFIX, D("1.08"))
    assert split(PREFIX) == (PREFIX, None)
    assert split("*1.05") == ("", D("1.05"))
    assert split(None) == ("", None)
    assert split("  ") == ("", None)


async def test_get_adjustment_parses_factor():
    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        return httpx.Response(200, json=_settings_payload(f"{PREFIX}*1.08"))

    adapter = adapter_with(handler)
    try:
        assert await adapter.get_channel_price_adjustment("337229", "airbnb") == D("1.08")
    finally:
        await adapter.aclose()


# --- Casos 2-3: composición preservando el prefijo --------------------------


async def _run_set(initial: str | None, factor: D | None, after: str | None):
    """Ejecuta set_channel_price_adjustment con GET inicial, POST y re-GET."""
    posted: list[dict] = []
    gets = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if (r := _token_ok(request)) is not None:
            return r
        if request.method == "POST":
            posted.append(json.loads(request.content))
            return httpx.Response(200, json={"success": True})
        gets["n"] += 1
        # 1er GET: estado inicial; siguientes: estado posterior
        return httpx.Response(
            200, json=_settings_payload(initial if gets["n"] == 1 else after)
        )

    adapter = adapter_with(handler)
    try:
        result = await adapter.set_channel_price_adjustment("337229", "airbnb", factor)
    finally:
        await adapter.aclose()
    return result, posted


async def test_set_adjustment_preserves_prefix():
    result, posted = await _run_set(PREFIX, D("1.08"), f"{PREFIX}*1.08")
    assert result.ok and result.verified
    written = posted[0][0]["properties"][0]["multiplier"]
    assert written == f"{PREFIX}*1.08"


async def test_set_adjustment_replaces_previous_factor():
    result, posted = await _run_set(f"{PREFIX}*1.02", D("1.10"), f"{PREFIX}*1.1")
    assert result.ok and result.verified
    assert posted[0][0]["properties"][0]["multiplier"] == f"{PREFIX}*1.1"


async def test_remove_adjustment_restores_exact_prefix():
    result, posted = await _run_set(f"{PREFIX}*1.08", None, PREFIX)
    assert result.ok and result.verified
    assert posted[0][0]["properties"][0]["multiplier"] == PREFIX


# --- Caso 5: prefijo vacío ---------------------------------------------------


async def test_set_adjustment_on_empty_multiplier():
    result, posted = await _run_set(None, D("1.05"), "*1.05")
    assert result.ok and result.verified
    assert posted[0][0]["properties"][0]["multiplier"] == "*1.05"


# --- Verificación Alpha: re-GET difiere → verified=False ---------------------


async def test_set_adjustment_unverified_when_reread_differs():
    result, _ = await _run_set(PREFIX, D("1.08"), PREFIX)  # el CM "no aplicó"
    assert result.ok
    assert result.verified is False
    assert "esperado" in (result.detail or "")


# --- Caso 4: canal no soportado ----------------------------------------------


async def test_unsupported_channel_rejected():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        if (r := _token_ok(request)) is not None:
            return r
        raise AssertionError("no debe llamar a la API para canal no soportado")

    adapter = adapter_with(handler)
    try:
        assert adapter.supports_price_adjustment("airbnb") is True
        assert adapter.supports_price_adjustment("booking") is False
        result = await adapter.set_channel_price_adjustment("337229", "booking", D("1.05"))
    finally:
        await adapter.aclose()
    assert result.ok is False


# --- Caso 6: alcance de canales en el body del fixed price -------------------


def _fp(channels=None) -> RemoteFixedPrice:
    return RemoteFixedPrice(
        offer_id=1,
        room_external_id="697411",
        first_night=date(2027, 5, 1),
        last_night=date(2027, 5, 10),
        name="PROMO",
        price=D("100000"),
        channels=channels,
    )


def test_fixed_price_body_with_scope_only_booking():
    adapter = Beds24V2Adapter(refresh_token="x", client=httpx.AsyncClient())
    body = adapter._fixed_price_body(_fp(channels={"airbnb": False}))
    assert body["channels"] == {"airbnb": {"enable": False}}
    assert "booking" not in body["channels"]  # solo tokens presentes


def test_fixed_price_body_without_scope_has_no_channels_key():
    adapter = Beds24V2Adapter(refresh_token="x", client=httpx.AsyncClient())
    body = adapter._fixed_price_body(_fp(channels=None))
    assert "channels" not in body
