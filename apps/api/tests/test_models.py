from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import ChannelKind, EventKind
from app.models.pricing import PricingRule
from app.models.property import Property, UnitType
from app.services import booking_service, event_service, pricing_service
from app.services.pricing_service import RuleViolation

DAY = date(2026, 7, 15)


async def make_unit(session, units: int = 1) -> tuple[Property, UnitType]:
    prop = Property(name="Casa Medellín")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="Apartaestudio", units_count=units)
    session.add(unit)
    await session.flush()
    return prop, unit


async def test_availability_shared(session):
    _, unit = await make_unit(session, units=1)
    await booking_service.create_booking(
        session,
        unit_type=unit,
        channel_kind=ChannelKind.booking,
        check_in=DAY,
        check_out=date(2026, 7, 16),
    )
    cd = await booking_service.ensure_calendar_day(session, unit, DAY)
    assert cd.units_available == 0


async def test_event_dedup(session):
    e1 = await event_service.upsert_event(
        session,
        name="Feria de Flores",
        start_date=date(2026, 8, 1),
        kind=EventKind.festival,
        location="Medellín",
    )
    e2 = await event_service.upsert_event(
        session,
        name="  feria de flores ",
        start_date=date(2026, 8, 1),
        kind=EventKind.festival,
        location="MEDELLÍN",
    )
    assert e1.id == e2.id


async def test_rule_violation(session):
    prop, unit = await make_unit(session)
    session.add(
        PricingRule(property_id=prop.id, min_price=Decimal("80000"), max_price=Decimal("500000"))
    )
    await session.flush()
    with pytest.raises(RuleViolation):
        await pricing_service.set_base_price(
            session,
            unit_type_id=unit.id,
            day=DAY,
            new_price=Decimal("50000"),
            property_id=prop.id,
        )
