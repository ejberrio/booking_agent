from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import ChangeOrigin
from app.models.property import Property, UnitType
from app.services import audit_service, pricing_service
from app.services.audit_service import RollbackConflict

DAY = date(2026, 7, 15)


async def make_unit(session) -> tuple[Property, UnitType]:
    prop = Property(name="Casa Medellín")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="Apartaestudio", units_count=1)
    session.add(unit)
    await session.flush()
    return prop, unit


async def test_change_creates_log(session):
    _, unit = await make_unit(session)
    log1 = await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("100000")
    )
    assert log1.old_price is None
    assert log1.new_price == Decimal("100000")
    assert log1.origin is ChangeOrigin.manual

    log2 = await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("120000")
    )
    assert log2.old_price == Decimal("100000")


async def test_rollback_restores(session):
    _, unit = await make_unit(session)
    await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("100000")
    )
    change = await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("120000")
    )
    rb = await audit_service.rollback_change(session, change.id)
    assert rb.origin is ChangeOrigin.rollback
    assert rb.new_price == Decimal("100000")
    assert rb.reverts_change_id == change.id
    assert await pricing_service.get_price(session, unit.id, DAY) == Decimal("100000")


async def test_rollback_conflict_requires_confirm(session):
    _, unit = await make_unit(session)
    await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("100000")
    )
    target = await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("120000")
    )
    # Cambio posterior sobre la misma (unidad, fecha)
    await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=DAY, new_price=Decimal("150000")
    )

    with pytest.raises(RollbackConflict):
        await audit_service.rollback_change(session, target.id)

    rb = await audit_service.rollback_change(session, target.id, confirm=True)
    assert rb.new_price == Decimal("100000")  # old_price del cambio objetivo
