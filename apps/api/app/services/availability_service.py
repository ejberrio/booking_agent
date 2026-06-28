"""Servicio de disponibilidad: bloquear (cerrar) y abrir (reabrir) noches.

Reutiliza el patrón de precios: preview → apply (con fingerprint) → publica a Beds24
→ audita. NUNCA altera noches con reserva confirmada (cero overbooking). La reversión
es la operación inversa (abrir deshace bloquear).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelManager
from app.models.availability import AvailabilityChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChangeOrigin
from app.models.property import UnitType
from app.schemas.pricing import (
    AvailabilityApplyResult,
    AvailabilityDayView,
    AvailabilityPreview,
    RangeSelection,
    availability_fingerprint,
)
from app.services import booking_service, sync_service

Action = Literal["block", "open"]
REINFORCE_DAYS = 14


async def _booked_nights(
    session: AsyncSession, unit_type_id: int, days: list[date]
) -> set[date]:
    """Noches cubiertas por una reserva confirmada (intocables)."""
    if not days:
        return set()
    res = await session.execute(
        select(Booking.check_in, Booking.check_out).where(
            Booking.unit_type_id == unit_type_id,
            Booking.status == BookingStatus.confirmed,
            Booking.check_in <= max(days),
            Booking.check_out > min(days),
        )
    )
    booked: set[date] = set()
    for check_in, check_out in res:
        d = check_in
        while d < check_out:
            booked.add(d)
            d += timedelta(days=1)
    return booked


async def _current(session: AsyncSession, unit_type_id: int, day: date) -> tuple[int | None, bool]:
    res = await session.execute(
        select(CalendarDay.units_available, CalendarDay.is_blocked).where(
            CalendarDay.unit_type_id == unit_type_id, CalendarDay.date == day
        )
    )
    row = res.first()
    if row is None:
        return None, False
    return int(row[0]), bool(row[1])


def _contiguous(days: list[date]) -> list[tuple[date, date]]:
    groups: list[list[date]] = []
    for d in sorted(days):
        if groups and groups[-1][1] + timedelta(days=1) == d:
            groups[-1][1] = d
        else:
            groups.append([d, d])
    return [(g[0], g[1]) for g in groups]


def _target(action: Action, unit: UnitType | None) -> int:
    return 0 if action == "block" else (unit.units_count if unit else 1)


async def preview(
    session: AsyncSession, *, unit_type_id: int, selection: RangeSelection, action: Action
) -> AvailabilityPreview:
    unit = await session.get(UnitType, unit_type_id)
    days = selection.expand()
    booked = await _booked_nights(session, unit_type_id, days)
    target = _target(action, unit)
    items: list[AvailabilityDayView] = []
    for d in days:
        cur_avail, cur_blocked = await _current(session, unit_type_id, d)
        if d in booked:
            items.append(AvailabilityDayView(d, cur_avail, cur_avail or 0, False, "reservada"))
            continue
        if action == "block" and cur_blocked:
            items.append(AvailabilityDayView(d, cur_avail, 0, False, "ya bloqueada"))
            continue
        if action == "open" and not cur_blocked and (cur_avail or 0) > 0:
            items.append(AvailabilityDayView(d, cur_avail, cur_avail or 0, False, "ya disponible"))
            continue
        items.append(AvailabilityDayView(d, cur_avail, target, True, None))
    affected = sum(1 for i in items if i.valid)
    return AvailabilityPreview(
        items=items,
        fingerprint=availability_fingerprint(items),
        affected_count=affected,
        skipped_count=len(items) - affected,
        reinforced=affected > REINFORCE_DAYS,
    )


async def apply(
    session: AsyncSession,
    channel: ChannelManager,
    *,
    unit_type_id: int,
    selection: RangeSelection,
    action: Action,
    fingerprint: str,
    origin: ChangeOrigin = ChangeOrigin.manual,
    message_id: int | None = None,
) -> AvailabilityApplyResult:
    prev = await preview(session, unit_type_id=unit_type_id, selection=selection, action=action)
    if prev.fingerprint != fingerprint:
        return AvailabilityApplyResult(stale=True)

    unit = await session.get(UnitType, unit_type_id)
    target = _target(action, unit)
    applied: list[date] = []
    skipped: list[tuple[date, str]] = []
    for item in prev.items:
        if not item.valid:
            skipped.append((item.date, item.skip_reason or "omitida"))
            continue
        cd = await booking_service.ensure_calendar_day(session, unit, item.date)
        session.add(
            AvailabilityChangeLog(
                unit_type_id=unit_type_id,
                date=item.date,
                old_units_available=cd.units_available,
                new_units_available=target,
                was_blocked=cd.is_blocked,
                is_blocked=(action == "block"),
                origin=origin,
                message_id=message_id,
            )
        )
        cd.units_available = target
        cd.is_blocked = action == "block"
        applied.append(item.date)
    await session.flush()

    published = issues = 0
    for start, end in _contiguous(applied):
        run = await sync_service.publish_availability(
            session, channel, unit_type_id=unit_type_id, date_from=start, date_to=end, num_avail=target
        )
        published += (end - start).days + 1
        issues += run.issue_count

    return AvailabilityApplyResult(
        applied=applied,
        skipped=skipped,
        audited=len(applied),
        published=published,
        publish_issues=issues,
    )
