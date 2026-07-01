"""Puerto provider-agnostic del Channel Manager y DTOs neutrales.

El sync_service depende de esta interfaz, NO de Beds24. Los DTOs son la
frontera: nada propietario de un proveedor cruza por aquí.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RemoteRoom:
    external_id: str
    name: str
    units_count: int = 1


@dataclass(frozen=True)
class RemoteProperty:
    external_id: str
    name: str
    currency: str = "COP"
    rooms: list[RemoteRoom] = field(default_factory=list)


@dataclass(frozen=True)
class RemoteRate:
    room_external_id: str
    date: date
    price: Decimal
    available: int = 0


@dataclass(frozen=True)
class RemoteBooking:
    external_id: str
    room_external_id: str
    check_in: date
    check_out: date
    status: str = "confirmed"


@dataclass(frozen=True)
class RemoteFixedPrice:
    """Una promoción publicable como 'fixed price' sobre una oferta.

    `external_id` None al crear; el canal devuelve su id, necesario para
    editar/retirar. `price_enabled=False` neutraliza (retira) el descuento.
    """

    offer_id: int
    room_external_id: str
    first_night: date
    last_night: date
    name: str
    price: Decimal
    external_id: int | None = None
    price_enabled: bool = True
    min_nights: int | None = None


@dataclass(frozen=True)
class WriteResult:
    ok: bool
    verified: bool
    detail: str | None = None


@dataclass(frozen=True)
class FixedPriceWriteResult:
    ok: bool
    verified: bool
    external_id: int | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RemoteOffer:
    offer_id: int
    name: str
    price: Decimal | None = None
    units_available: int | None = None


@dataclass(frozen=True)
class ConnectionInfo:
    ok: bool
    properties: list[RemoteProperty] = field(default_factory=list)
    detail: str | None = None


@runtime_checkable
class ChannelManager(Protocol):
    """Interfaz común que todo Channel Manager debe implementar."""

    async def test_connection(self) -> ConnectionInfo: ...

    async def get_properties(self) -> list[RemoteProperty]: ...

    async def get_rates(
        self, room_external_id: str, date_from: date, date_to: date
    ) -> list[RemoteRate]: ...

    async def get_bookings(
        self, property_external_id: str, since: date | None = None
    ) -> list[RemoteBooking]: ...

    async def set_rate(
        self, room_external_id: str, day: date, price: Decimal
    ) -> WriteResult: ...

    async def set_rate_range(
        self, room_external_id: str, date_from: date, date_to: date, price: Decimal
    ) -> WriteResult: ...

    async def set_availability_range(
        self, room_external_id: str, date_from: date, date_to: date, num_avail: int
    ) -> WriteResult: ...

    # --- Promociones vía 'fixed price' sobre una oferta (feature 011) ---

    async def set_fixed_price(self, fp: RemoteFixedPrice) -> FixedPriceWriteResult:
        """Crea (sin external_id) o modifica (con external_id) una promoción."""
        ...

    async def get_fixed_prices(self, room_external_id: str) -> list[RemoteFixedPrice]: ...

    async def disable_fixed_price(
        self, external_id: int, room_external_id: str
    ) -> FixedPriceWriteResult:
        """Neutraliza (retira) una promoción: price_enabled=False."""
        ...

    async def get_offers(
        self,
        property_external_id: str,
        room_external_id: str,
        arrival: date,
        departure: date,
        num_adults: int = 2,
    ) -> list[RemoteOffer]: ...
