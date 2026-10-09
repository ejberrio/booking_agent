"""Capa de aplicación del motor de precios.

Orquesta el dominio (effective_price, violates_rule) y los servicios de la
feature 001 (pricing_service, audit_service), y publica el PRECIO EFECTIVO al
Channel Manager (puerto de la feature 002). Toda escritura: validar → auditar →
publicar; rango/bulk con preview + confirmación (huella anti-obsolescencia).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelManager
from app.domain.pricing import PromotionLike, effective_price, violates_rule
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.enums import BookingStatus, ChangeOrigin, ChannelKind, PromotionStatus
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
    """Vista del calendario del rango en lote: 3 consultas en total (antes ~5 por día,
    ~10 s por mes contra la BD de producción)."""
    unit = await session.get(UnitType, unit_type_id)
    if unit is None:
        return []
    rates = {
        r.date: r.base_price
        for r in (
            await session.execute(
                select(Rate).where(
                    Rate.unit_type_id == unit_type_id,
                    Rate.date >= date_from,
                    Rate.date <= date_to,
                    Rate.base_price > 0,  # ≤ 0 = sin precio (feature 023)
                )
            )
        ).scalars()
    }
    cal = {
        c.date: (int(c.units_available), bool(c.is_blocked))
        for c in (
            await session.execute(
                select(CalendarDay).where(
                    CalendarDay.unit_type_id == unit_type_id,
                    CalendarDay.date >= date_from,
                    CalendarDay.date <= date_to,
                )
            )
        ).scalars()
    }
    promos = list(
        (
            await session.execute(
                select(Promotion).where(
                    Promotion.property_id == unit.property_id,
                    Promotion.status == PromotionStatus.active,
                )
            )
        ).scalars()
    )
    likes = [
        PromotionLike(p.discount_type, p.discount_value, p.start_date, p.end_date, True)
        for p in promos
    ]
    views: list[CalendarDayView] = []
    for day in _date_range(date_from, date_to):
        base = rates.get(day)
        avail, blocked = cal.get(day, (None, False))
        views.append(
            CalendarDayView(
                date=day,
                base_price=base,
                effective_price=effective_price(base, likes, day) if base is not None else None,
                available=avail,
                is_blocked=blocked,
                promotions=[p.name for p in promos if p.start_date <= day <= p.end_date],
            )
        )
    return views


async def get_kpis(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> dict:
    """KPIs del rango: noches reservadas por canal y noches bloqueadas.

    Una noche pertenece al rango si su fecha ∈ [date_from, date_to]; una reserva
    ocupa las noches [check_in, check_out). Los bloqueos son globales (cierran
    todos los canales a la vez), por eso no llevan desglose por canal.
    """
    rows = (
        await session.execute(
            select(Booking.channel_kind, Booking.check_in, Booking.check_out).where(
                Booking.unit_type_id == unit_type_id,
                Booking.status == BookingStatus.confirmed,
                Booking.check_in <= date_to,
                Booking.check_out > date_from,
            )
        )
    ).all()
    nights: dict[str, int] = {kind.value: 0 for kind in ChannelKind}
    for kind, check_in, check_out in rows:
        first = max(check_in, date_from)
        last = min(check_out, date_to + timedelta(days=1))
        nights[kind.value] += max(0, (last - first).days)

    blocked = (
        await session.execute(
            select(func.count()).where(
                CalendarDay.unit_type_id == unit_type_id,
                CalendarDay.date >= date_from,
                CalendarDay.date <= date_to,
                CalendarDay.is_blocked.is_(True),
            )
        )
    ).scalar_one()

    return {
        "date_from": date_from,
        "date_to": date_to,
        "reserved_nights": nights,
        "total_reserved": sum(nights.values()),
        "blocked_nights": int(blocked),
    }


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
