"""Adaptador Beds24 API V2 (token) que implementa el puerto ChannelManager.

V2 es la API soportada por Beds24. La V1 está deprecada y sus ESCRITURAS no
funcionan (setRoomDates responde "items updated: 0" para cualquier campo), por
lo que mover precios — el núcleo del sistema — requiere V2.

Autenticación: un `refreshToken` (no expira si se usa cada 30 días) se canjea por
un `token` de 24h vía GET /authentication/token; el token se cachea y se renueva
solo. Las escrituras de precio van a POST /inventory/rooms/calendar.

Las pruebas usan httpx.MockTransport, sin llamar a la API real.
"""

from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.channels.base import (
    ConnectionInfo,
    FixedPriceWriteResult,
    RemoteBooking,
    RemoteFixedPrice,
    RemoteOffer,
    RemoteProperty,
    RemoteRate,
    RemoteRoom,
    WriteResult,
)
from app.channels.errors import AuthError, ChannelError, RateLimited

_AUTH_HINTS = ("token", "auth", "credential", "scope", "permission", "forbidden")
_RATE_HINTS = ("limit", "credit", "too many", "rate")


def _days(date_from: date, date_to: date) -> list[date]:
    return [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]


class Beds24V2Adapter:
    def __init__(
        self,
        *,
        refresh_token: str | None,
        prop_id: str | None = None,
        room_id: str | None = None,
        base_url: str = "https://api.beds24.com/v2",
        client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
    ) -> None:
        self.refresh_token = refresh_token or ""
        self.prop_id = prop_id
        self.room_id = room_id
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._token: str | None = None
        self._token_exp: float = 0.0

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _redact(self, text: str) -> str:
        out = text
        for secret in (self.refresh_token, self._token):
            if secret:
                out = out.replace(secret, "***")
        return out

    def _classify(self, message: str) -> ChannelError:
        low = message.lower()
        if any(h in low for h in _AUTH_HINTS):
            return AuthError(self._redact(message))
        if any(h in low for h in _RATE_HINTS):
            return RateLimited(self._redact(message))
        return ChannelError(self._redact(message))

    async def _backoff(self, attempt: int) -> None:
        if self.retry_base_delay:
            await asyncio.sleep(self.retry_base_delay * (2**attempt))

    async def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_exp - 60:
            return self._token
        try:
            resp = await self._client.get(
                f"{self._base_url}/authentication/token",
                headers={"refreshToken": self.refresh_token},
            )
        except httpx.HTTPError as exc:
            raise ChannelError(self._redact(f"auth: {exc}")) from exc
        data = resp.json()
        if resp.status_code != 200 or not isinstance(data, dict) or not data.get("token"):
            detail = str(data.get("error")) if isinstance(data, dict) else "sin token"
            raise AuthError(self._redact(f"no se pudo obtener token V2: {detail}"))
        self._token = str(data["token"])
        self._token_exp = now + float(data.get("expiresIn", 86400))
        return self._token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> Any:
        url = f"{self._base_url}/{path}"
        last_exc: ChannelError | None = None
        for attempt in range(self.max_retries):
            token = await self._ensure_token()
            try:
                resp = await self._client.request(
                    method, url, params=params, json=json_body, headers={"token": token}
                )
            except httpx.HTTPError as exc:
                last_exc = ChannelError(self._redact(f"comunicación: {exc}"))
                await self._backoff(attempt)
                continue

            if resp.status_code == 401:  # token rechazado -> forzar renovación
                self._token = None
                last_exc = AuthError("token V2 rechazado (401)")
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
            if isinstance(data, dict) and data.get("success") is False:
                err = self._classify(str(data.get("error") or data.get("errors") or "error V2"))
                if isinstance(err, RateLimited):
                    last_exc = err
                    await self._backoff(attempt)
                    continue
                raise err
            return data

        raise last_exc or ChannelError("operación fallida")

    # --- Puerto ChannelManager ---

    async def get_properties(self) -> list[RemoteProperty]:
        data = await self._request("GET", "properties", params={"includeAllRooms": "true"})
        out: list[RemoteProperty] = []
        for p in data.get("data", []):
            rooms = [
                RemoteRoom(str(r["id"]), r.get("name", ""), int(r.get("qty", 1) or 1))
                for r in p.get("roomTypes", [])
            ]
            out.append(
                RemoteProperty(
                    external_id=str(p["id"]),
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
        # V2 devuelve {"data":[{"roomId","calendar":[{"from","to","numAvail","price1"}]}]}
        # con rangos; se expanden a días.
        data = await self._request(
            "GET",
            "inventory/rooms/calendar",
            params={
                "roomId": room_external_id,
                "startDate": date_from.isoformat(),
                "endDate": date_to.isoformat(),
                "includePrices": "true",
                "includeNumAvail": "true",
            },
        )
        out: list[RemoteRate] = []
        for room in data.get("data", []):
            for entry in room.get("calendar", []):
                try:
                    span_from = date.fromisoformat(entry["from"])
                    span_to = date.fromisoformat(entry["to"])
                except (KeyError, ValueError, TypeError):
                    continue
                price = Decimal(str(entry.get("price1", 0) or 0))
                avail = int(entry.get("numAvail", 0) or 0)
                for day in _days(span_from, span_to):
                    out.append(
                        RemoteRate(
                            room_external_id=room_external_id,
                            date=day,
                            price=price,
                            available=avail,
                        )
                    )
        return out

    async def get_bookings(
        self, property_external_id: str, since: date | None = None
    ) -> list[RemoteBooking]:
        # V2: {"data":[{"id","roomId","arrival","departure","status"}]}; departure = checkout.
        params: dict[str, Any] = {"propertyId": property_external_id}
        if since is not None:
            params["arrivalFrom"] = since.isoformat()
        data = await self._request("GET", "bookings", params=params)
        out: list[RemoteBooking] = []
        for b in data.get("data", []):
            try:
                check_in = date.fromisoformat(b["arrival"])
                check_out = date.fromisoformat(b["departure"])
            except (KeyError, ValueError, TypeError):
                continue
            status = "cancelled" if str(b.get("status")) == "cancelled" else "confirmed"
            out.append(
                RemoteBooking(
                    external_id=str(b["id"]),
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
        body = [
            {
                "roomId": int(room_external_id),
                "calendar": [
                    {
                        "from": date_from.isoformat(),
                        "to": date_to.isoformat(),
                        "price1": float(price),
                    }
                ],
            }
        ]
        result = await self._request("POST", "inventory/rooms/calendar", json_body=body)
        ok = False
        if isinstance(result, list) and result:
            ok = bool(result[0].get("success"))
        elif isinstance(result, dict):
            ok = bool(result.get("success"))
        # Verificación: releer y comparar.
        rates = await self.get_rates(room_external_id, date_from, date_to)
        days = _days(date_from, date_to)
        verified = ok and len(rates) == len(days) and all(r.price == price for r in rates)
        detail = None if verified else "el precio no se confirmó al releer"
        return WriteResult(ok=ok, verified=verified, detail=detail)

    async def set_availability_range(
        self, room_external_id: str, date_from: date, date_to: date, num_avail: int
    ) -> WriteResult:
        body = [
            {
                "roomId": int(room_external_id),
                "calendar": [
                    {
                        "from": date_from.isoformat(),
                        "to": date_to.isoformat(),
                        "numAvail": int(num_avail),
                    }
                ],
            }
        ]
        result = await self._request("POST", "inventory/rooms/calendar", json_body=body)
        ok = False
        if isinstance(result, list) and result:
            ok = bool(result[0].get("success"))
        elif isinstance(result, dict):
            ok = bool(result.get("success"))
        # Verificación: releer y comparar la disponibilidad.
        rates = await self.get_rates(room_external_id, date_from, date_to)
        days = _days(date_from, date_to)
        verified = ok and len(rates) == len(days) and all(r.available == num_avail for r in rates)
        detail = None if verified else "la disponibilidad no se confirmó al releer"
        return WriteResult(ok=ok, verified=verified, detail=detail)

    # --- Promociones vía fixed price sobre una oferta (feature 011) ---

    def _fixed_price_body(self, fp: RemoteFixedPrice) -> dict[str, Any]:
        item: dict[str, Any] = {
            "offerId": fp.offer_id,
            "roomId": int(fp.room_external_id),
            "firstNight": fp.first_night.isoformat(),
            "lastNight": fp.last_night.isoformat(),
            "name": fp.name,
            "roomPrice": float(fp.price),
            "roomPriceEnable": fp.price_enabled,
        }
        if self.prop_id:
            item["propertyId"] = int(self.prop_id)
        if fp.external_id is not None:
            item["id"] = fp.external_id
        if fp.min_nights is not None:
            item["minNights"] = int(fp.min_nights)
        return item

    async def set_fixed_price(self, fp: RemoteFixedPrice) -> FixedPriceWriteResult:
        result = await self._request(
            "POST", "inventory/fixedPrices", json_body=[self._fixed_price_body(fp)]
        )
        ok = False
        external_id = fp.external_id
        # Respuesta: {"success":true,"data":[{... "id": N ...}]} o lista de resultados.
        payload = result.get("data") if isinstance(result, dict) else result
        if isinstance(result, dict):
            ok = bool(result.get("success", True))
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                ok = bool(first.get("success", ok))
                new_id = first.get("id") or (first.get("new") or {}).get("id")
                if new_id is not None:
                    external_id = int(new_id)
        detail = None if ok else "el canal no confirmó la escritura del fixed price"
        return FixedPriceWriteResult(ok=ok, verified=ok, external_id=external_id, detail=detail)

    async def get_fixed_prices(self, room_external_id: str) -> list[RemoteFixedPrice]:
        params: dict[str, Any] = {"roomId": room_external_id}
        if self.prop_id:
            params["propertyId"] = self.prop_id
        data = await self._request("GET", "inventory/fixedPrices", params=params)
        out: list[RemoteFixedPrice] = []
        for fp in data.get("data", []) if isinstance(data, dict) else []:
            try:
                first_night = date.fromisoformat(fp["firstNight"])
                last_night = date.fromisoformat(fp["lastNight"])
            except (KeyError, ValueError, TypeError):
                continue
            out.append(
                RemoteFixedPrice(
                    offer_id=int(fp.get("offerId", 0) or 0),
                    room_external_id=str(fp.get("roomId", room_external_id)),
                    first_night=first_night,
                    last_night=last_night,
                    name=str(fp.get("name", "")),
                    price=Decimal(str(fp.get("roomPrice", 0) or 0)),
                    external_id=int(fp["id"]) if fp.get("id") is not None else None,
                    price_enabled=bool(fp.get("roomPriceEnable", True)),
                    min_nights=int(fp["minNights"]) if fp.get("minNights") else None,
                )
            )
        return out

    async def disable_fixed_price(
        self, external_id: int, room_external_id: str
    ) -> FixedPriceWriteResult:
        item: dict[str, Any] = {
            "id": external_id,
            "roomId": int(room_external_id),
            "roomPriceEnable": False,
        }
        if self.prop_id:
            item["propertyId"] = int(self.prop_id)
        result = await self._request("POST", "inventory/fixedPrices", json_body=[item])
        ok = bool(result.get("success", True)) if isinstance(result, dict) else True
        detail = None if ok else "el canal no confirmó la neutralización"
        return FixedPriceWriteResult(ok=ok, verified=ok, external_id=external_id, detail=detail)

    async def get_offers(
        self,
        property_external_id: str,
        room_external_id: str,
        arrival: date,
        departure: date,
        num_adults: int = 2,
    ) -> list[RemoteOffer]:
        data = await self._request(
            "GET",
            "inventory/rooms/offers",
            params={
                "propertyId": property_external_id,
                "roomId": room_external_id,
                "arrival": arrival.isoformat(),
                "departure": departure.isoformat(),
                "numAdults": num_adults,
            },
        )
        out: list[RemoteOffer] = []
        for room in data.get("data", []) if isinstance(data, dict) else []:
            for offer in room.get("offers", []):
                out.append(
                    RemoteOffer(
                        offer_id=int(offer.get("offerId", 0) or 0),
                        name=str(offer.get("offerName", "")),
                        price=Decimal(str(offer["price"])) if offer.get("price") is not None else None,
                        units_available=(
                            int(offer["unitsAvailable"])
                            if offer.get("unitsAvailable") is not None
                            else None
                        ),
                    )
                )
        return out
