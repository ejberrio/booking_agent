from datetime import date

import pytest
from sqlalchemy import func, select

from app.channels.base import WriteResult
from app.channels.errors import ChannelError
from app.models.availability import AvailabilityChangeLog
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Channel, Property, UnitType
from app.schemas.pricing import RangeSelection
from app.services import availability_service, booking_service

pytestmark = pytest.mark.anyio


class FakeCM:
    def __init__(self):
        self.published: list = []

    async def set_availability_range(self, room, df, dt, num_avail):
        self.published.append((room, df, dt, num_avail))
        return WriteResult(True, True)


class BoomCM:
    async def set_availability_range(self, room, df, dt, num_avail):
        raise ChannelError("beds24 caído")


async def make_unit(session):
    prop = Property(name="Casa")
    session.add(prop)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="r1")
    session.add(unit)
    await session.flush()
    return unit


async def _cd(session, unit_id, day):
    return (
        await session.execute(
            select(CalendarDay).where(CalendarDay.unit_type_id == unit_id, CalendarDay.date == day)
        )
    ).scalar_one_or_none()


async def _apply(session, cm, unit, action, df, dt):
    sel = RangeSelection(df, dt)
    prev = await availability_service.preview(
        session, unit_type_id=unit.id, selection=sel, action=action
    )
    return await availability_service.apply(
        session, cm, unit_type_id=unit.id, selection=sel, action=action, fingerprint=prev.fingerprint
    )


async def test_block_skips_booked_night(session):
    unit = await make_unit(session)
    cm = FakeCM()
    # Reserva confirmada el 2 de julio (1 noche: 2->3).
    await booking_service.create_booking(
        session,
        unit_type=unit,
        channel_kind=ChannelKind.booking,
        check_in=date(2026, 7, 2),
        check_out=date(2026, 7, 3),
        status=BookingStatus.confirmed,
    )
    res = await _apply(session, cm, unit, "block", date(2026, 7, 1), date(2026, 7, 3))

    assert res.applied == [date(2026, 7, 1), date(2026, 7, 3)]  # 2 jul omitido (reservado)
    assert any(d == date(2026, 7, 2) and r == "reservada" for d, r in res.skipped)
    cd1 = await _cd(session, unit.id, date(2026, 7, 1))
    assert cd1.is_blocked is True and cd1.units_available == 0
    assert res.published == 2 and res.publish_issues == 0
    logs = int((await session.execute(select(func.count()).select_from(AvailabilityChangeLog))).scalar_one())
    assert logs == 2  # un log por noche afectada (no por la omitida)


async def test_open_restores_blocked_night(session):
    unit = await make_unit(session)
    cm = FakeCM()
    await _apply(session, cm, unit, "block", date(2026, 8, 1), date(2026, 8, 1))
    cd = await _cd(session, unit.id, date(2026, 8, 1))
    assert cd.is_blocked is True

    res = await _apply(session, cm, unit, "open", date(2026, 8, 1), date(2026, 8, 1))
    cd = await _cd(session, unit.id, date(2026, 8, 1))
    assert res.applied == [date(2026, 8, 1)]
    assert cd.is_blocked is False and cd.units_available == unit.units_count


async def test_open_does_not_touch_reserved(session):
    unit = await make_unit(session)
    cm = FakeCM()
    await booking_service.create_booking(
        session,
        unit_type=unit,
        channel_kind=ChannelKind.booking,
        check_in=date(2026, 9, 5),
        check_out=date(2026, 9, 6),
        status=BookingStatus.confirmed,
    )
    res = await _apply(session, cm, unit, "open", date(2026, 9, 5), date(2026, 9, 5))
    cd = await _cd(session, unit.id, date(2026, 9, 5))
    assert res.applied == []  # noche reservada se omite
    assert cd.units_available == 0  # sigue ocupada por la reserva


async def test_block_is_idempotent(session):
    unit = await make_unit(session)
    cm = FakeCM()
    await _apply(session, cm, unit, "block", date(2026, 10, 1), date(2026, 10, 1))
    res = await _apply(session, cm, unit, "block", date(2026, 10, 1), date(2026, 10, 1))
    assert res.applied == []  # ya bloqueada -> 0 afectadas


async def test_publish_resilient_records_issue(session):
    unit = await make_unit(session)
    res = await _apply(session, BoomCM(), unit, "block", date(2026, 11, 1), date(2026, 11, 1))
    # El cambio local se conserva aunque la publicación falle.
    cd = await _cd(session, unit.id, date(2026, 11, 1))
    assert cd.is_blocked is True
    assert res.applied == [date(2026, 11, 1)]
    assert res.publish_issues == 1
