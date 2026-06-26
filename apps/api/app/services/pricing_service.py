"""Servicio de precios: fija el precio base y registra auditoría (principio III)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.pricing import PromotionLike, effective_price, violates_rule
from app.models.audit import PriceChangeLog
from app.models.calendar import Rate
from app.models.enums import ChangeOrigin, PromotionStatus
from app.models.pricing import PricingRule, Promotion


class RuleViolation(ValueError):
    """Se lanza cuando un precio queda fuera de los límites de la PricingRule activa."""


async def _get_rate(session: AsyncSession, unit_type_id: int, day: date) -> Rate | None:
    res = await session.execute(
        select(Rate).where(Rate.unit_type_id == unit_type_id, Rate.date == day)
    )
    return res.scalar_one_or_none()


async def get_price(session: AsyncSession, unit_type_id: int, day: date) -> Decimal | None:
    rate = await _get_rate(session, unit_type_id, day)
    return rate.base_price if rate else None


async def _active_rule(session: AsyncSession, property_id: int) -> PricingRule | None:
    res = await session.execute(
        select(PricingRule).where(
            PricingRule.property_id == property_id, PricingRule.is_active.is_(True)
        )
    )
    return res.scalars().first()


async def get_active_rule(session: AsyncSession, property_id: int) -> PricingRule | None:
    """Regla de precio activa de la propiedad (público para la capa de aplicación)."""
    return await _active_rule(session, property_id)


async def _promotions_for(session: AsyncSession, property_id: int) -> list[PromotionLike]:
    res = await session.execute(
        select(Promotion).where(
            Promotion.property_id == property_id,
            Promotion.status == PromotionStatus.active,
        )
    )
    return [
        PromotionLike(p.discount_type, p.discount_value, p.start_date, p.end_date, True)
        for p in res.scalars()
    ]


async def get_effective_price(
    session: AsyncSession, property_id: int, unit_type_id: int, day: date
) -> Decimal | None:
    base = await get_price(session, unit_type_id, day)
    if base is None:
        return None
    promos = await _promotions_for(session, property_id)
    return effective_price(base, promos, day)


async def set_base_price(
    session: AsyncSession,
    *,
    unit_type_id: int,
    day: date,
    new_price: Decimal,
    origin: ChangeOrigin = ChangeOrigin.manual,
    property_id: int | None = None,
    message_id: int | None = None,
    suggestion_id: int | None = None,
    validate_rule: bool = True,
) -> PriceChangeLog:
    """Fija el precio base de (unidad, día) y crea una entrada de auditoría."""
    if validate_rule and property_id is not None:
        rule = await _active_rule(session, property_id)
        if rule and violates_rule(new_price, rule.min_price, rule.max_price):
            raise RuleViolation(
                f"Precio {new_price} fuera de [{rule.min_price}, {rule.max_price}]"
            )

    rate = await _get_rate(session, unit_type_id, day)
    old_price = rate.base_price if rate else None
    if rate:
        rate.base_price = new_price
    else:
        session.add(Rate(unit_type_id=unit_type_id, date=day, base_price=new_price))

    log = PriceChangeLog(
        unit_type_id=unit_type_id,
        date=day,
        old_price=old_price,
        new_price=new_price,
        origin=origin,
        message_id=message_id,
        suggestion_id=suggestion_id,
    )
    session.add(log)
    await session.flush()
    return log
