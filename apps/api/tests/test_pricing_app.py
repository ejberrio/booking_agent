from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.channels.base import WriteResult
from app.models.audit import PriceChangeLog
from app.models.enums import ChannelKind, PromotionStatus, PromotionType
from app.models.pricing import PricingRule, Promotion
from app.models.property import Channel, Property, UnitType
from app.schemas.pricing import RangeSelection
from app.services import pricing_app_service, pricing_service
from app.services.audit_service import RollbackConflict

D = Decimal


class FakeCM:
    def __init__(self):
        self.published: list = []

    async def set_rate(self, room, day, price):
        return await self.set_rate_range(room, day, day, price)

    async def set_rate_range(self, room, df, dt, price):
        self.published.append((room, df, dt, price))
        return WriteResult(True, True)


async def make_unit(session, *, min_price=None, max_price=None):
    prop = Property(name="Casa")
    session.add(prop)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="r1")
    session.add(unit)
    await session.flush()
    if min_price is not None or max_price is not None:
        session.add(PricingRule(property_id=prop.id, min_price=min_price, max_price=max_price))
        await session.flush()
    return prop, unit


async def _count(session, model) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_get_calendar_base_and_effective(session):
    prop, unit = await make_unit(session)
    day = date(2026, 7, 15)
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=day, new_price=D("180000"))
    session.add(
        Promotion(
            property_id=prop.id,
            name="P10",
            discount_type=PromotionType.percent,
            discount_value=D("10"),
            start_date=day,
            end_date=day,
            status=PromotionStatus.active,
        )
    )
    await session.flush()

    views = await pricing_app_service.get_calendar(session, unit.id, day, day)
    assert views[0].base_price == D("180000")
    assert views[0].effective_price == D("162000")
    assert "P10" in views[0].promotions


async def test_set_day_validates_and_publishes(session):
    prop, unit = await make_unit(session, min_price=D("80000"))
    cm = FakeCM()
    day = date(2026, 7, 15)

    r = await pricing_app_service.set_day_price(
        session, cm, unit_type_id=unit.id, day=day, price=D("120000")
    )
    assert r.applied_days == [day]
    assert r.audited == 1
    assert cm.published  # se publicó el efectivo
    assert await _count(session, PriceChangeLog) == 1

    r2 = await pricing_app_service.set_day_price(
        session, cm, unit_type_id=unit.id, day=date(2026, 7, 16), price=D("50000")
    )
    assert r2.skipped_invalid == [date(2026, 7, 16)]
    assert r2.audited == 0
    assert await _count(session, PriceChangeLog) == 1  # el inválido no se auditó


async def test_preview_apply_weekday_stale_and_invalid(session):
    prop, unit = await make_unit(session, min_price=D("80000"))
    cm = FakeCM()
    sel = RangeSelection(date(2026, 7, 13), date(2026, 7, 19), weekdays=[4, 5])  # viernes y sábado

    preview = await pricing_app_service.preview_range(
        session, unit_type_id=unit.id, selection=sel, price=D("200000")
    )
    days = [i.date for i in preview.items]
    assert days and all(d.weekday() in (4, 5) for d in days)
    assert preview.has_invalid is False

    stale = await pricing_app_service.apply_range(
        session, cm, unit_type_id=unit.id, selection=sel, price=D("200000"), fingerprint="bad"
    )
    assert stale.stale is True
    assert stale.applied_days == []

    applied = await pricing_app_service.apply_range(
        session, cm, unit_type_id=unit.id, selection=sel, price=D("200000"),
        fingerprint=preview.fingerprint,
    )
    assert set(applied.applied_days) == set(days)
    assert applied.audited == len(days)

    inv = await pricing_app_service.preview_range(
        session, unit_type_id=unit.id, selection=sel, price=D("10000")
    )
    assert inv.has_invalid is True
    inv_apply = await pricing_app_service.apply_range(
        session, cm, unit_type_id=unit.id, selection=sel, price=D("10000"),
        fingerprint=inv.fingerprint,
    )
    assert inv_apply.applied_days == []
    assert len(inv_apply.skipped_invalid) == len(days)


async def test_rollback_restores_and_publishes(session):
    prop, unit = await make_unit(session)
    cm = FakeCM()
    day = date(2026, 7, 15)
    await pricing_app_service.set_day_price(session, cm, unit_type_id=unit.id, day=day, price=D("100000"))
    await pricing_app_service.set_day_price(session, cm, unit_type_id=unit.id, day=day, price=D("120000"))

    target = (
        await session.execute(
            select(PriceChangeLog).where(PriceChangeLog.new_price == D("120000"))
        )
    ).scalars().first()
    rb = await pricing_app_service.rollback_and_publish(session, cm, target.id)
    assert rb.applied_days == [day]
    assert await pricing_service.get_price(session, unit.id, day) == D("100000")


async def test_rollback_conflict_requires_confirm(session):
    prop, unit = await make_unit(session)
    cm = FakeCM()
    day = date(2026, 7, 20)
    await pricing_app_service.set_day_price(session, cm, unit_type_id=unit.id, day=day, price=D("100000"))
    await pricing_app_service.set_day_price(session, cm, unit_type_id=unit.id, day=day, price=D("120000"))
    target = (
        await session.execute(
            select(PriceChangeLog).where(
                PriceChangeLog.new_price == D("120000"), PriceChangeLog.date == day
            )
        )
    ).scalars().first()
    await pricing_app_service.set_day_price(session, cm, unit_type_id=unit.id, day=day, price=D("150000"))

    with pytest.raises(RollbackConflict):
        await pricing_app_service.rollback_and_publish(session, cm, target.id)

    rb = await pricing_app_service.rollback_and_publish(session, cm, target.id, confirm=True)
    assert rb.applied_days == [day]


async def test_range_selection_empty_weekdays_means_all_days(session):
    from app.schemas.pricing import RangeSelection

    sel = RangeSelection(date(2026, 9, 1), date(2026, 9, 10), weekdays=[])
    assert len(sel.expand()) == 10  # lista vacía = todos los días (no 0)
