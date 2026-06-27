"""Capa de aplicación del motor de precios.

Orquesta el dominio (effective_price, violates_rule) y los servicios de la
feature 001 (pricing_service, audit_service), y publica el PRECIO EFECTIVO al
Channel Manager (puerto de la feature 002). Toda escritura: validar → auditar →
publicar; rango/bulk con preview + confirmación (huella anti-obsolescencia).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelManager
from app.domain.pricing import violates_rule
from app.models.audit import PriceChangeLog
from app.models.calendar import CalendarDay
from app.models.enums import ChangeOrigin, PromotionStatus
from app.models.pricing import Promotion
from app.models.property import UnitType
from app.schemas.pricing import (
    ApplyResult,
    CalendarDayView,
    ChangePreview,
    ChangePreviewDay,
    RangeSelection,
    fingerprint_for,
)
from app.services import audit_service, pricing_service, sync_service


def _date_range(date_from: date, date_to: date) -> list[date]:
    return [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]


async def _availability(session: AsyncSession, unit_type_id: int, day: date) -> int | None:
    res = await session.execute(
        select(CalendarDay.units_available).where(
            CalendarDay.unit_type_id == unit_type_id, CalendarDay.date == day
        )
    )
    val = res.scalar_one_or_none()
    # None = no hay datos sincronizados para ese día (distinto de 0 = sin disponibilidad).
    return int(val) if val is not None else None


async def _active_promo_names(session: AsyncSession, property_id: int, day: date) -> list[str]:
    res = await session.execute(
        select(Promotion.name).where(
            Promotion.property_id == property_id,
            Promotion.status == PromotionStatus.active,
            Promotion.start_date <= day,
            Promotion.end_date >= day,
        )
    )
    return [n for n in res.scalars()]


def _group_contiguous(eff: dict[date, Decimal]) -> list[tuple[date, date, Decimal]]:
    groups: list[list] = []
    for d, p in sorted(eff.items()):
        if groups and groups[-1][1] + timedelta(days=1) == d and groups[-1][2] == p:
            groups[-1][1] = d
        else:
            groups.append([d, d, p])
    return [(g[0], g[1], g[2]) for g in groups]


# --------- operaciones públicas ---------


async def get_calendar(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> list[CalendarDayView]:
    unit = await session.get(UnitType, unit_type_id)
    if unit is None:
        return []
    views: list[CalendarDayView] = []
    for day in _date_range(date_from, date_to):
        base = await pricing_service.get_price(session, unit_type_id, day)
        eff = (
            await pricing_service.get_effective_price(session, unit.property_id, unit_type_id, day)
            if base is not None
            else None
        )
        views.append(
            CalendarDayView(
                date=day,
                base_price=base,
                effective_price=eff,
                available=await _availability(session, unit_type_id, day),
                promotions=await _active_promo_names(session, unit.property_id, day),
            )
        )
    return views


async def publish_effective(
    session: AsyncSession, channel: ChannelManager, unit_type_id: int, days: list[date]
) -> tuple[int, int]:
    """Publica el precio efectivo de `days`, agrupando días contiguos con igual valor."""
    if not days:
        return (0, 0)
    unit = await session.get(UnitType, unit_type_id)
    eff: dict[date, Decimal] = {}
    for d in days:
        e = await pricing_service.get_effective_price(session, unit.property_id, unit_type_id, d)
        if e is not None:
            eff[d] = e
    published = issues = 0
    for start, end, price in _group_contiguous(eff):
        run = await sync_service.publish_price(
            session, channel, unit_type_id=unit_type_id, date_from=start, date_to=end, price=price
        )
        published += (end - start).days + 1
        issues += run.issue_count
    return (published, issues)


async def set_day_price(
    session: AsyncSession,
    channel: ChannelManager,
    *,
    unit_type_id: int,
    day: date,
    price: Decimal,
    origin: ChangeOrigin = ChangeOrigin.manual,
    message_id: int | None = None,
) -> ApplyResult:
    unit = await session.get(UnitType, unit_type_id)
    rule = await pricing_service.get_active_rule(session, unit.property_id)
    if rule and violates_rule(price, rule.min_price, rule.max_price):
        return ApplyResult(skipped_invalid=[day])

    await pricing_service.set_base_price(
        session,
        unit_type_id=unit_type_id,
        day=day,
        new_price=price,
        origin=origin,
        property_id=unit.property_id,
        message_id=message_id,
        validate_rule=False,
    )
    published, issues = await publish_effective(session, channel, unit_type_id, [day])
    return ApplyResult(applied_days=[day], audited=1, published=published, publish_issues=issues)


async def preview_range(
    session: AsyncSession, *, unit_type_id: int, selection: RangeSelection, price: Decimal
) -> ChangePreview:
    unit = await session.get(UnitType, unit_type_id)
    rule = await pricing_service.get_active_rule(session, unit.property_id)
    invalid = bool(rule and violates_rule(price, rule.min_price, rule.max_price))
    items: list[ChangePreviewDay] = []
    for d in selection.expand():
        old = await pricing_service.get_price(session, unit_type_id, d)
        items.append(
            ChangePreviewDay(
                date=d,
                old_price=old,
                new_price=price,
                valid=not invalid,
                reason="fuera de límites" if invalid else None,
            )
        )
    valid_count = sum(1 for i in items if i.valid)
    return ChangePreview(
        items=items,
        fingerprint=fingerprint_for(items),
        has_invalid=any(not i.valid for i in items),
        valid_count=valid_count,
        invalid_count=len(items) - valid_count,
    )


async def apply_range(
    session: AsyncSession,
    channel: ChannelManager,
    *,
    unit_type_id: int,
    selection: RangeSelection,
    price: Decimal,
    fingerprint: str,
    origin: ChangeOrigin = ChangeOrigin.manual,
    message_id: int | None = None,
) -> ApplyResult:
    preview = await preview_range(
        session, unit_type_id=unit_type_id, selection=selection, price=price
    )
    if preview.fingerprint != fingerprint:
        return ApplyResult(stale=True)

    unit = await session.get(UnitType, unit_type_id)
    applied: list[date] = []
    skipped: list[date] = []
    for item in preview.items:
        if not item.valid:
            skipped.append(item.date)
            continue
        await pricing_service.set_base_price(
            session,
            unit_type_id=unit_type_id,
            day=item.date,
            new_price=price,
            origin=origin,
            property_id=unit.property_id,
            message_id=message_id,
            validate_rule=False,
        )
        applied.append(item.date)

    published, issues = await publish_effective(session, channel, unit_type_id, applied)
    return ApplyResult(
        applied_days=applied,
        skipped_invalid=skipped,
        audited=len(applied),
        published=published,
        publish_issues=issues,
    )


async def rollback_and_publish(
    session: AsyncSession, channel: ChannelManager, change_id: int, *, confirm: bool = False
) -> ApplyResult:
    log = await audit_service.rollback_change(session, change_id, confirm=confirm)
    published, issues = await publish_effective(session, channel, log.unit_type_id, [log.date])
    return ApplyResult(
        applied_days=[log.date], audited=1, published=published, publish_issues=issues
    )


async def history(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> list[PriceChangeLog]:
    res = await session.execute(
        select(PriceChangeLog)
        .where(
            PriceChangeLog.unit_type_id == unit_type_id,
            PriceChangeLog.date >= date_from,
            PriceChangeLog.date <= date_to,
        )
        .order_by(PriceChangeLog.id)
    )
    return list(res.scalars())
