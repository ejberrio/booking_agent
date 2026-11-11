"""Channel Manager SIMULADO para el ambiente de pruebas (feature 026, CHANNEL_MODE=simulated).

Responde con los datos de la propia base (los de la cuenta de la sesión) y acepta las
escrituras sin enviarlas a ningún lado: NUNCA habla con Beds24, Booking.com ni Airbnb.
Así el ambiente de pruebas puede usar una copia de los datos reales sin riesgo de publicar
un precio, abrir una fecha o tocar una reserva de verdad.

Los servicios de la app actualizan la base después de una escritura "exitosa", así que las
lecturas siguientes ya reflejan el cambio (la "verdad remota" simulada es la base local).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import (
    CalendarEntry,
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
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.property import Property, UnitType

_fixed_ids = count(900_000_000)
OK = WriteResult(True, True, "simulado: no se envió a ningún canal")


# Mensajes simulados (feature 045): en memoria por cuenta, solo para el ambiente de pruebas.
_SIM_MESSAGES: dict[int, list[dict]] = {}


class SimulatedChannelAdapter:
    """Implementa `ChannelManager` sobre la base de la cuenta de la sesión."""

    simulated = True

    def __init__(self, session: AsyncSession):
        self.session = session

    async def aclose(self) -> None:
        return None

    # --- Mensajes simulados (feature 045) ---

    async def _sim_messages(self) -> list[dict]:
        from datetime import UTC, datetime

        from app.db.tenancy import current_account_id
        from app.models.booking import Booking

        acc = current_account_id(self.session) or 0
        if acc not in _SIM_MESSAGES:
            rows = (await self.session.execute(
                select(Booking).where(Booking.external_ref.is_not(None)).order_by(Booking.check_in.desc())
            )).scalars().all()[:3]
            now = datetime.now(UTC).isoformat()
            _SIM_MESSAGES[acc] = [
                {"id": 900000 + i, "bookingId": b.external_ref, "source": "guest", "read": False,
                 "time": now, "message": "Hola, ¿a qué hora podemos hacer el check-in? Llegamos en la tarde."}
                for i, b in enumerate(rows)
            ]
        return _SIM_MESSAGES[acc]

    async def get_messages(self, *, booking_ids=None, max_age=90, unread_only=False, max_pages=5):
        msgs = await self._sim_messages()
        if booking_ids:
            msgs = [m for m in msgs if str(m["bookingId"]) in {str(b) for b in booking_ids}]
        if unread_only:
            msgs = [m for m in msgs if not m.get("read")]
        return [dict(m) for m in msgs]

    async def send_message(self, booking_id: str, text: str) -> None:
        from datetime import UTC, datetime

        msgs = await self._sim_messages()
        msgs.append({"id": 900000 + len(msgs) + 100, "bookingId": str(booking_id), "source": "host",
                     "read": True, "time": datetime.now(UTC).isoformat(), "message": text})

    async def mark_messages_read(self, booking_id: str) -> None:
        for m in await self._sim_messages():
            if str(m["bookingId"]) == str(booking_id):
                m["read"] = True

    async def _unit(self, room_external_id: str) -> UnitType | None:
        return (
            await self.session.execute(
                select(UnitType).where(UnitType.external_ref == str(room_external_id))
            )
        ).scalar_one_or_none()

    async def get_properties(self) -> list[RemoteProperty]:
        props = list((await self.session.execute(select(Property).order_by(Property.id))).scalars())
        out: list[RemoteProperty] = []
        for p in props:
            if not p.external_ref:
                continue
            units = (
                await self.session.execute(
                    select(UnitType).where(UnitType.property_id == p.id).order_by(UnitType.id)
                )
            ).scalars()
            rooms = [
                RemoteRoom(u.external_ref, u.name, u.units_count) for u in units if u.external_ref
            ]
            out.append(
                RemoteProperty(
                    p.external_ref, p.name, p.currency, rooms, address=p.address,
                    latitude=p.latitude, longitude=p.longitude,
                )
            )
        return out

    async def test_connection(self) -> ConnectionInfo:
        return ConnectionInfo(True, await self.get_properties(), "modo simulado")

    async def get_rates(
        self, room_external_id: str, date_from: date, date_to: date
    ) -> list[RemoteRate]:
        unit = await self._unit(room_external_id)
        if unit is None:
            return []
        prices = dict(
            (
                await self.session.execute(
                    select(Rate.date, Rate.base_price).where(
                        Rate.unit_type_id == unit.id, Rate.date >= date_from, Rate.date <= date_to
                    )
                )
            ).all()
        )
        avail = dict(
            (
                await self.session.execute(
                    select(CalendarDay.date, CalendarDay.units_available).where(
                        CalendarDay.unit_type_id == unit.id,
                        CalendarDay.date >= date_from,
                        CalendarDay.date <= date_to,
                    )
                )
            ).all()
        )
        out: list[RemoteRate] = []
        d = date_from
        while d <= date_to:
            if d in prices or d in avail:
                out.append(
                    RemoteRate(
                        str(room_external_id), d, Decimal(prices.get(d) or 0),
                        int(avail.get(d, unit.units_count if d in prices else 0)),
                    )
                )
            d += timedelta(days=1)
        return out

    async def get_bookings(
        self, property_external_id: str, since: date | None = None
    ) -> list[RemoteBooking]:
        rows = (
            await self.session.execute(
                select(Booking, UnitType.external_ref)
                .join(UnitType, Booking.unit_type_id == UnitType.id)
                .join(Property, UnitType.property_id == Property.id)
                .where(Property.external_ref == str(property_external_id))
            )
        ).all()
        return [
            RemoteBooking(
                b.external_ref or f"sim-{b.id}", room or "", b.check_in, b.check_out,
                status=b.status.value, channel=b.channel_kind.value, guest_name=b.guest_name,
            )
            for b, room in rows
        ]

    async def set_rate(self, room_external_id: str, day: date, price: Decimal) -> WriteResult:
        return OK

    async def set_rate_range(
        self, room_external_id: str, date_from: date, date_to: date, price: Decimal
    ) -> WriteResult:
        return OK

    async def set_availability_range(
        self, room_external_id: str, date_from: date, date_to: date, num_avail: int
    ) -> WriteResult:
        return OK

    async def set_calendar_entries(
        self, room_external_id: str, entries: list[CalendarEntry]
    ) -> WriteResult:
        return OK

    async def set_fixed_price(self, fp: RemoteFixedPrice) -> FixedPriceWriteResult:
        return FixedPriceWriteResult(True, True, fp.external_id or next(_fixed_ids), "simulado")

    async def get_fixed_prices(self, room_external_id: str) -> list[RemoteFixedPrice]:
        return []

    async def disable_fixed_price(
        self, external_id: int, room_external_id: str
    ) -> FixedPriceWriteResult:
        return FixedPriceWriteResult(True, True, external_id, "simulado")

    async def get_offers(
        self,
        property_external_id: str,
        room_external_id: str,
        arrival: date,
        departure: date,
        num_adults: int = 2,
    ) -> list[RemoteOffer]:
        return []

    def supports_price_adjustment(self, channel: str) -> bool:
        return channel in ("booking", "airbnb")

    async def get_channel_price_adjustment(
        self, property_external_id: str, channel: str
    ) -> Decimal | None:
        return None

    async def set_channel_price_adjustment(
        self, property_external_id: str, channel: str, factor: Decimal | None
    ) -> WriteResult:
        return OK


MANUAL_OK = WriteResult(True, True, "sin conexión: registrado en StayLever; aplícalo a mano")


class ManualChannelAdapter(SimulatedChannelAdapter):
    """Modo sin conexión (feature 029): la "verdad" es la base de StayLever.

    Mismo comportamiento que el canal simulado, pero para cuentas reales que no conectaron
    un Channel Manager: los cambios se registran y la app recuerda aplicarlos a mano.
    """

    simulated = False
    manual = True
