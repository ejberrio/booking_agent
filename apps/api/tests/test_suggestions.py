from datetime import date
from decimal import Decimal

from app.models.enums import SuggestionStatus
from app.models.market import PriceSuggestion
from app.models.property import Property, UnitType
from app.services import pricing_service, suggestion_service

DAY = date(2026, 7, 15)


async def make_unit(session) -> tuple[Property, UnitType]:
    prop = Property(name="Casa Medellín")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="Apartaestudio", units_count=1)
    session.add(unit)
    await session.flush()
    return prop, unit


async def test_suggestion_apply_links_change(session):
    prop, unit = await make_unit(session)
    sug = PriceSuggestion(
        property_id=prop.id,
        unit_type_id=unit.id,
        date_from=DAY,
        date_to=DAY,
        suggested_price=Decimal("200000"),
        rationale={"events": ["Feria de Flores"], "occupancy": 0.9},
        confidence=Decimal("0.800"),
        status=SuggestionStatus.proposed,
    )
    session.add(sug)
    await session.flush()

    await suggestion_service.approve(session, sug.id)
    logs = await suggestion_service.apply(session, sug.id)

    await session.refresh(sug)
    assert sug.status is SuggestionStatus.applied
    assert sug.applied_change_id == logs[0].id
    assert await pricing_service.get_price(session, unit.id, DAY) == Decimal("200000")
