"""Servicio de reservas/disponibilidad. La disponibilidad es por unidad (compartida)."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import UnitType


def _nights(check_in: date, check_out: date) -> list[date]:
    return [check_in + timedelta(days=i) for i in range((check_out - check_in).days)]


async def ensure_calendar_day(
    session: AsyncSession, unit_type: UnitType, day: date
) -> CalendarDay:
    res = await session.execute(
        select(CalendarDay).where(
            CalendarDay.unit_type_id == unit_type.id, CalendarDay.date == day
        )
    )
    cd = res.scalar_one_or_none()
    if cd is None:
        cd = CalendarDay(
            unit_type_id=unit_type.id, date=day, units_available=unit_type.units_count
        )
        session.add(cd)
        await session.flush()
    return cd


async def block_day(session: AsyncSession, unit_type: UnitType, day: date) -> CalendarDay:
    cd = await ensure_calendar_day(session, unit_type, day)
    cd.is_blocked = True
    cd.units_available = 0
    await session.flush()
    return cd


async def create_booking(
    session: AsyncSession,
    *,
    unit_type: UnitType,
    channel_kind: ChannelKind,
    check_in: date,
    check_out: date,
    status: BookingStatus = BookingStatus.confirmed,
    external_ref: str | None = None,
) -> Booking:
    """Crea una reserva y, si está confirmada, reduce la disponibilidad de cada noche.

    La reducción es a nivel de unidad, sin importar el canal: vender en un canal
    bloquea la noche para todos (cero overbooking).
    """
    booking = Booking(
        unit_type_id=unit_type.id,
        channel_kind=channel_kind,
        check_in=check_in,
        check_out=check_out,
        status=status,
        external_ref=external_ref,
    )
    session.add(booking)

    if status is BookingStatus.confirmed:
        for night in _nights(check_in, check_out):
            cd = await ensure_calendar_day(session, unit_type, night)
            cd.units_available = max(0, cd.units_available - 1)

    await session.flush()
    return booking
