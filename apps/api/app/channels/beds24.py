"""Adaptador Beds24 (API V1 JSON) que implementa el puerto ChannelManager.

Autenticación con la API Key de cuenta (Allow Writes = Yes), sin propKey.
Las respuestas/payloads siguen una forma V1 representativa; los nombres exactos
se confirman contra la documentación de Beds24 en la integración real. Las
pruebas usan httpx.MockTransport, sin llamar a la API real.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.channels.base import (
    ConnectionInfo,
    RemoteBooking,
    RemoteProperty,
    RemoteRate,
    RemoteRoom,
    WriteResult,
)
from app.channels.errors import AuthError, ChannelError, RateLimited

_AUTH_HINTS = ("api key", "apikey", "credential", "auth", "permission", "not allowed")
_RATE_HINTS = ("limit", "credit", "too many", "rate")


def _days(date_from: date, date_to: date) -> list[date]:
    return [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]


def _parse_compact_date(key: str) -> date | None:
    """Convierte una clave 'YYYYMMDD' de Beds24 a date."""
    if len(key) != 8 or not key.isdigit():
        return None
    try:
        return date(int(key[:4]), int(key[4:6]), int(key[6:8]))
    except ValueError:
        return None


class Beds24Adapter:
    def __init__(
        self,
        *,
        api_key: str | None,
        prop_key: str | None = None,
        prop_id: str | None = None,
        room_id: str | None = None,
        base_url: str = "https://api.beds24.com/json",
        client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
    ) -> None:
        self.api_key = api_key or ""
        self.prop_key = prop_key
        self.prop_id = prop_id
        self.room_id = room_id
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _redact(self, text: str) -> str:
        return text.replace(self.api_key, "***") if self.api_key else text

    def _classify(self, message: str) -> ChannelError:
        low = message.lower()
        if any(h in low for h in _AUTH_HINTS):
            return AuthError(self._redact(message))
        if any(h in low for h in _RATE_HINTS):
            return RateLimited(self._redact(message))
        return ChannelError(self._redact(message))

    async def _request(self, endpoint: str, params: dict[str, Any]) -> Any:
        url = f"{self._base_url}/{endpoint}"
        auth: dict[str, str] = {"apiKey": self.api_key}
        if self.prop_key:
            auth["propKey"] = self.prop_key
        body = {"authentication": auth, **params}
        last_exc: ChannelError | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await self._client.post(url, json=body)
            except httpx.HTTPError as exc:  # error de comunicación
                last_exc = ChannelError(self._redact(f"comunicación: {exc}"))
                await self._backoff(attempt)
                continue

            if resp.status_code == 429:
                last_exc = RateLimited("rate limit (HTTP 429)")
                await self._backoff(attempt)
                continue
            if resp.status_code >= 500:
                last_exc = ChannelError(f"servidor ({resp.status_code})")
                await self._backoff(attempt)
                continue

            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                err = self._classify(str(data["error"]))
                if isinstance(err, RateLimited):
                    last_exc = err
                    await self._backoff(attempt)
                    continue
                raise err
            return data

        raise last_exc or ChannelError("operación fallida")

    async def _backoff(self, attempt: int) -> None:
        if self.retry_base_delay:
            await asyncio.sleep(self.retry_base_delay * (2**attempt))

    # --- Puerto ChannelManager ---

    async def get_properties(self) -> list[RemoteProperty]:
        # Beds24 V1 devuelve {"getProperties": [{..., "roomTypes": [...]}]}.
        data = await self._request("getProperties", {})
        items = data.get("getProperties", []) if isinstance(data, dict) else data
        out: list[RemoteProperty] = []
        for p in items:
            rooms = [
                RemoteRoom(str(r["roomId"]), r.get("name", ""), int(float(r.get("qty", 1) or 1)))
                for r in p.get("roomTypes", [])
            ]
            out.append(
                RemoteProperty(
                    external_id=str(p["propId"]),
                    name=p.get("name", ""),
                    currency=p.get("currency", "COP"),
                    rooms=rooms,
                )
            )
        return out

    async def test_connection(self) -> ConnectionInfo:
        props = await self.get_properties()
        return ConnectionInfo(ok=True, properties=props)

    async def get_rates(
        self, room_external_id: str, date_from: date, date_to: date
    ) -> list[RemoteRate]:
        # Beds24 V1 devuelve {"YYYYMMDD": {"i": numAvail, "p1": price}, ...}.
        data = await self._request(
            "getRoomDates",
            {
                "roomId": room_external_id,
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
            },
        )
        out: list[RemoteRate] = []
        if isinstance(data, dict):
            for key, val in data.items():
                day = _parse_compact_date(key)
                if day is None or not isinstance(val, dict):
                    continue
                out.append(
                    RemoteRate(
                        room_external_id=room_external_id,
                        date=day,
                        price=Decimal(str(val.get("p1", "0"))),
                        available=int(val.get("i", 0)),
                    )
                )
        return out

    async def get_bookings(
        self, property_external_id: str, since: date | None = None
    ) -> list[RemoteBooking]:
        # Beds24 V1 devuelve una lista con firstNight/lastNight; checkout = lastNight + 1.
        params: dict[str, Any] = {"propId": property_external_id}
        if since is not None:
            params["modifiedSince"] = since.isoformat()
        data = await self._request("getBookings", params)
        rows = data if isinstance(data, list) else data.get("bookings", [])
        out: list[RemoteBooking] = []
        for b in rows:
            try:
                check_in = date.fromisoformat(b["firstNight"])
                check_out = date.fromisoformat(b["lastNight"]) + timedelta(days=1)
            except (KeyError, ValueError):
                continue
            status = "cancelled" if str(b.get("status")) == "0" else "confirmed"
            out.append(
                RemoteBooking(
                    external_id=str(b["bookId"]),
                    room_external_id=str(b["roomId"]),
                    check_in=check_in,
                    check_out=check_out,
                    status=status,
                )
            )
        return out

    async def set_rate(
        self, room_external_id: str, day: date, price: Decimal
    ) -> WriteResult:
        return await self.set_rate_range(room_external_id, day, day, price)

    async def set_rate_range(
        self, room_external_id: str, date_from: date, date_to: date, price: Decimal
    ) -> WriteResult:
        days = _days(date_from, date_to)
        # Beds24 V1 usa claves de fecha compactas 'YYYYMMDD' y 'price1'.
        dates_payload = {d.strftime("%Y%m%d"): {"price1": float(price)} for d in days}
        await self._request(
            "setRoomDates",
            {"roomId": room_external_id, "dates": dates_payload},
        )
        # Verificación: releer y comparar.
        rates = await self.get_rates(room_external_id, date_from, date_to)
        verified = len(rates) == len(days) and all(r.price == price for r in rates)
        detail = None if verified else "el precio no se confirmó al releer"
        return WriteResult(ok=True, verified=verified, detail=detail)

    async def set_availability_range(
        self, room_external_id: str, date_from: date, date_to: date, num_avail: int
    ) -> WriteResult:
        # Las escrituras de la API V1 no funcionan; producción usa V2.
        raise ChannelError("La API V1 no soporta escritura de disponibilidad; usa la V2.")
