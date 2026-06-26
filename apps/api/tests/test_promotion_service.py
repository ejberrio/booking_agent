from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.channels.base import WriteResult
from app.models.audit import PromotionChangeLog
from app.models.enums import PromotionAction, PromotionType
from app.models.property import Property, UnitType
from app.services import pricing_service, promotion_service

D = Decimal
DAY = date(2026, 7, 15)


class FakeCM:
    def __init__(self):
        self.published: list = []

    async def set_rate(self, room, day, price):
        return await self.set_rate_range(room, day, day, price)

    async def set_rate_range(self, room, df, dt, price):
        self.published.append((room, df, dt, price))
        return WriteResult(True, True)


async def make_unit_with_price(session, *, price=D("180000")):
    prop = Property(name="Casa")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="r1")
    session.add(unit)
    await session.flush()
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=DAY, new_price=price)
    return prop, unit


async def test_create_promo_audits_and_republishes(session):
    prop, unit = await make_unit_with_price(session)
    cm = FakeCM()
    await promotion_service.create_promotion(
        session,
        cm,
        property_id=prop.id,
        name="P15",
        discount_type=PromotionType.percent,
        discount_value=D("15"),
        start_date=DAY,
        end_date=DAY,
    )
    log = (await session.execute(select(PromotionChangeLog))).scalars().first()
    assert log.action is PromotionAction.created
    assert cm.published  # se re-publicó el efectivo
    eff = await pricing_service.get_effective_price(session, prop.id, unit.id, DAY)
    assert eff == D("153000")  # 180000 - 15%


async def test_overlap_takes_max_discount(session):
    prop, unit = await make_unit_with_price(session)
    cm = FakeCM()
    await promotion_service.create_promotion(
        session, cm, property_id=prop.id, name="P10",
        discount_type=PromotionType.percent, discount_value=D("10"), start_date=DAY, end_date=DAY,
    )
    await promotion_service.create_promotion(
        session, cm, property_id=prop.id, name="P20",
        discount_type=PromotionType.percent, discount_value=D("20"), start_date=DAY, end_date=DAY,
    )
    eff = await pricing_service.get_effective_price(session, prop.id, unit.id, DAY)
    assert eff == D("144000")  # solo 20% (no 30%)


async def test_delete_promo_restores_base(session):
    prop, unit = await make_unit_with_price(session)
    cm = FakeCM()
    promo = await promotion_service.create_promotion(
        session, cm, property_id=prop.id, name="P15",
        discount_type=PromotionType.percent, discount_value=D("15"), start_date=DAY, end_date=DAY,
    )
    await promotion_service.delete_promotion(session, cm, promo.id)
    eff = await pricing_service.get_effective_price(session, prop.id, unit.id, DAY)
    assert eff == D("180000")  # vuelve al base
    actions = [
        log.action
        for log in (
            await session.execute(select(PromotionChangeLog).order_by(PromotionChangeLog.id))
        ).scalars()
    ]
    assert PromotionAction.deleted in actions
