"""Feature 012: import multi-canal — canal real en reservas, corrección en
re-import y upsert de canales desde configuración. Doble in-memory del puerto.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.channels.base import (
    ConnectionInfo,
    RemoteBooking,
    RemoteProperty,
    RemoteRate,
    RemoteRoom,
)
from app.core.config import settings
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Channel
from app.services import sync_service

D = Decimal
DAY = date(2026, 7, 15)


class FakeCM:
    """Channel Manager falso que reporta reservas con canal de origen."""

    def __init__(self, bookings=None):
        self.properties = [
            RemoteProperty("337229", "Apto", "COP", [RemoteRoom("697411", "3BR", 1)])
        ]
        self._bookings = bookings or []

    async def test_connection(self):
        return ConnectionInfo(True, self.properties)

    async def get_properties(self):
        return self.properties

    async def get_rates(self, room, df, dt):
        return [RemoteRate("697411", DAY, D("180000"), 1)]

    async def get_bookings(self, prop, since=None):
        return self._bookings


def _rb(ext_id: str, channel: str | None, status: str = "confirmed") -> RemoteBooking:
    return RemoteBooking(
        external_id=ext_id,
        room_external_id="697411",
        check_in=date(2026, 8, 6),
        check_out=date(2026, 8, 19),
        status=status,
        channel=channel,
    )


async def _bookings_by_ref(session) -> dict[str, Booking]:
    rows = (await session.execute(select(Booking))).scalars().all()
    return {b.external_ref: b for b in rows}


# ---------------------------------------------------------------------------
# T006 — import con orígenes mixtos
# ---------------------------------------------------------------------------


async def test_import_records_real_channel_per_booking(session):
    fake = FakeCM(
        bookings=[
            _rb("b1", "booking"),
            _rb("b2", "airbnb"),
            _rb("b3", None),  # reserva manual: sin origen
            _rb("b4", "expedia"),  # origen no contemplado
        ]
    )
    run = await sync_service.import_remote(session, fake, DAY, DAY)

    by_ref = await _bookings_by_ref(session)
    assert by_ref["b1"].channel_kind == ChannelKind.booking
    assert by_ref["b2"].channel_kind == ChannelKind.airbnb
    # Desconocido/ausente → direct, y el lote NUNCA aborta.
    assert by_ref["b3"].channel_kind == ChannelKind.direct
    assert by_ref["b4"].channel_kind == ChannelKind.direct
    assert run.created_count == 5  # 4 reservas + 1 tarifa del baseline
    assert len(by_ref) == 4


def test_map_channel_normalization():
    m = sync_service._map_channel
    assert m("booking") == ChannelKind.booking
    assert m("booking.com") == ChannelKind.booking
    assert m("airbnb") == ChannelKind.airbnb
    assert m("airbnb.com") == ChannelKind.airbnb
    assert m(None) == ChannelKind.direct
    assert m("") == ChannelKind.direct
    assert m("vrbo") == ChannelKind.direct


# ---------------------------------------------------------------------------
# T007 — corrección en re-import, sin duplicados
# ---------------------------------------------------------------------------


async def test_reimport_fixes_wrong_channel_without_duplicates(session):
    # 1) Import inicial que (simulando el bug histórico) queda como booking.
    await sync_service.import_remote(session, FakeCM(bookings=[_rb("air-1", None)]), DAY, DAY)
    by_ref = await _bookings_by_ref(session)
    assert by_ref["air-1"].channel_kind == ChannelKind.direct  # sin origen → direct

    # Forzar el estado histórico incorrecto (todo era booking antes de la feature).
    by_ref["air-1"].channel_kind = ChannelKind.booking
    await session.flush()

    # 2) Re-import: el remoto ahora reporta el origen real (airbnb).
    run = await sync_service.import_remote(session, FakeCM(bookings=[_rb("air-1", "airbnb")]), DAY, DAY)

    by_ref = await _bookings_by_ref(session)
    assert len(by_ref) == 1  # 0 duplicados (dedupe por external_ref)
    assert by_ref["air-1"].channel_kind == ChannelKind.airbnb
    assert run.created_count == 0
    assert run.updated_count >= 1  # la corrección cuenta como update


async def test_reimport_keeps_channel_when_already_correct(session):
    fake = FakeCM(bookings=[_rb("b1", "booking")])
    await sync_service.import_remote(session, fake, DAY, DAY)
    run2 = await sync_service.import_remote(session, fake, DAY, DAY)
    by_ref = await _bookings_by_ref(session)
    assert by_ref["b1"].channel_kind == ChannelKind.booking
    assert len(by_ref) == 1
    assert run2.created_count == 0


async def test_cancelled_remote_booking_keeps_its_channel(session):
    # Fuera de alcance el sync de status (issue #91): aquí solo se garantiza que
    # una reserva cuyo estado cambió en el canal conserva su canal en re-import.
    await sync_service.import_remote(session, FakeCM(bookings=[_rb("c1", "airbnb")]), DAY, DAY)
    await sync_service.import_remote(
        session, FakeCM(bookings=[_rb("c1", "airbnb", status="cancelled")]), DAY, DAY
    )
    by_ref = await _bookings_by_ref(session)
    assert by_ref["c1"].channel_kind == ChannelKind.airbnb
    assert by_ref["c1"].status == BookingStatus.confirmed  # status NO se toca (issue #91)


# ---------------------------------------------------------------------------
# T008 — upsert de canales desde configuración
# ---------------------------------------------------------------------------


async def _channels(session) -> dict[ChannelKind, Channel]:
    rows = (await session.execute(select(Channel))).scalars().all()
    return {c.kind: c for c in rows}


async def test_channels_upserted_from_config(session, monkeypatch):
    monkeypatch.setattr(settings, "channels_active", "booking, airbnb")
    await sync_service.import_remote(session, FakeCM(), DAY, DAY)

    channels = await _channels(session)
    assert channels[ChannelKind.booking].is_active is True
    assert channels[ChannelKind.airbnb].is_active is True
    assert ChannelKind.direct not in channels  # solo lo configurado

    # No duplica en re-import (constraint uq_channel_property_kind).
    await sync_service.import_remote(session, FakeCM(), DAY, DAY)
    count = (await session.execute(select(func.count()).select_from(Channel))).scalar_one()
    assert count == 2


async def test_removing_channel_from_config_deactivates_it(session, monkeypatch):
    monkeypatch.setattr(settings, "channels_active", "booking,airbnb")
    await sync_service.import_remote(
        session, FakeCM(bookings=[_rb("a1", "airbnb")]), DAY, DAY
    )

    # "Desconectar" Airbnb = quitarlo de la config.
    monkeypatch.setattr(settings, "channels_active", "booking")
    await sync_service.import_remote(session, FakeCM(), DAY, DAY)

    channels = await _channels(session)
    assert channels[ChannelKind.booking].is_active is True
    assert channels[ChannelKind.airbnb].is_active is False  # inactivo, no borrado
    # Las reservas históricas del canal desactivado se conservan.
    by_ref = await _bookings_by_ref(session)
    assert by_ref["a1"].channel_kind == ChannelKind.airbnb


async def test_config_tolerates_garbage(monkeypatch):
    monkeypatch.setattr(settings, "channels_active", " booking , NADA, airbnb ,, airbnb ")
    assert settings.active_channel_kinds() == [ChannelKind.booking, ChannelKind.airbnb]
