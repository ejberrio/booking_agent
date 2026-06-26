"""Gestión de promociones: CRUD + auditoría (PromotionChangeLog) + re-publicación
del precio efectivo de los días afectados (las promos no se mapean a las nativas).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import PromotionChangeLog
from app.models.calendar import Rate
from app.models.enums import ChangeOrigin, PromotionAction, PromotionStatus, PromotionType
from app.models.pricing import Promotion
from app.models.property import UnitType
from app.services import pricing_app_service


def _snapshot(p: Promotion) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "discount_type": p.discount_type.value,
        "discount_value": str(p.discount_value),
        "start_date": p.start_date.isoformat(),
        "end_date": p.end_date.isoformat(),
        "status": p.status.value,
    }


async def _affected_days_by_unit(
    session: AsyncSession, property_id: int, start: date, end: date
) -> dict[int, list[date]]:
    res = await session.execute(
        select(Rate.unit_type_id, Rate.date)
        .join(UnitType, UnitType.id == Rate.unit_type_id)
        .where(UnitType.property_id == property_id, Rate.date >= start, Rate.date <= end)
    )
    by_unit: dict[int, list[date]] = {}
    for unit_id, d in res.all():
        by_unit.setdefault(unit_id, []).append(d)
    return by_unit


async def _republish(session, channel, property_id: int, start: date, end: date) -> int:
    issues = 0
    affected = await _affected_days_by_unit(session, property_id, start, end)
    for unit_id, days in affected.items():
        _, iss = await pricing_app_service.publish_effective(session, channel, unit_id, days)
        issues += iss
    return issues


async def create_promotion(
    session: AsyncSession,
    channel,
    *,
    property_id: int,
    name: str,
    discount_type: PromotionType,
    discount_value: Decimal,
    start_date: date,
    end_date: date,
    conditions: dict | None = None,
    origin: ChangeOrigin = ChangeOrigin.manual,
) -> Promotion:
    promo = Promotion(
        property_id=property_id,
        name=name,
        discount_type=discount_type,
        discount_value=discount_value,
        start_date=start_date,
        end_date=end_date,
        conditions=conditions,
        status=PromotionStatus.active,
    )
    session.add(promo)
    await session.flush()

    session.add(
        PromotionChangeLog(
            promotion_id=promo.id, action=PromotionAction.created, after=_snapshot(promo), origin=origin
        )
    )
    await session.flush()
    await _republish(session, channel, property_id, start_date, end_date)
    return promo


async def update_promotion(
    session: AsyncSession,
    channel,
    promotion_id: int,
    *,
    name: str | None = None,
    discount_type: PromotionType | None = None,
    discount_value: Decimal | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status: PromotionStatus | None = None,
    origin: ChangeOrigin = ChangeOrigin.manual,
) -> Promotion:
    promo = await session.get(Promotion, promotion_id)
    if promo is None:
        raise ValueError(f"No existe la promoción {promotion_id}")
    before = _snapshot(promo)
    old_start, old_end = promo.start_date, promo.end_date

    if name is not None:
        promo.name = name
    if discount_type is not None:
        promo.discount_type = discount_type
    if discount_value is not None:
        promo.discount_value = discount_value
    if start_date is not None:
        promo.start_date = start_date
    if end_date is not None:
        promo.end_date = end_date
    if status is not None:
        promo.status = status
    await session.flush()

    session.add(
        PromotionChangeLog(
            promotion_id=promo.id,
            action=PromotionAction.updated,
            before=before,
            after=_snapshot(promo),
            origin=origin,
        )
    )
    await session.flush()
    await _republish(
        session,
        channel,
        promo.property_id,
        min(old_start, promo.start_date),
        max(old_end, promo.end_date),
    )
    return promo


async def delete_promotion(
    session: AsyncSession, channel, promotion_id: int, *, origin: ChangeOrigin = ChangeOrigin.manual
) -> None:
    promo = await session.get(Promotion, promotion_id)
    if promo is None:
        raise ValueError(f"No existe la promoción {promotion_id}")
    before = _snapshot(promo)
    property_id, start, end = promo.property_id, promo.start_date, promo.end_date

    await session.delete(promo)
    await session.flush()

    session.add(
        PromotionChangeLog(
            promotion_id=None, action=PromotionAction.deleted, before=before, origin=origin
        )
    )
    await session.flush()
    await _republish(session, channel, property_id, start, end)
