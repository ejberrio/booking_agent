"""Feature 026 (principio VI): el agente de la cuenta B no ve ni propone cambios sobre A,
aunque el LLM le pase identificadores de A."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.agent import orchestrator, tools
from app.models.agent import AgentAction, Conversation
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.enums import (
    AgentActionStatus,
    BookingStatus,
    ChangeOrigin,
    ChannelKind,
    PromotionType,
)
from app.models.pricing import Promotion
from app.models.property import Property, UnitType
from app.services import pricing_service

pytestmark = pytest.mark.anyio

D1 = date.today() + timedelta(days=10)


async def _seed(session, name, ref):
    prop = Property(name=f"Casa {name}", city="Medellín", external_ref=ref)
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name=f"{name}-3BR", external_ref=f"{ref}-r")
    session.add(unit)
    await session.flush()
    await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=D1, new_price=Decimal("300000"),
        origin=ChangeOrigin.manual,
    )
    promo = Promotion(property_id=prop.id, unit_type_id=unit.id, name=f"Promo {name}",
                      discount_type=PromotionType.percent, discount_value=Decimal("10"),
                      start_date=D1, end_date=D1)
    conv = Conversation()
    booking = Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking, check_in=D1,
                      check_out=D1 + timedelta(days=2), status=BookingStatus.confirmed,
                      external_ref=f"bk-{name}")
    session.add_all([promo, conv, booking])
    await session.flush()
    action = AgentAction(conversation_id=conv.id, tool="propose_set_day",
                         arguments={"unit_type_id": unit.id, "day": str(D1), "price": 1},
                         status=AgentActionStatus.proposed)
    session.add(action)
    await session.commit()
    change = (await session.execute(select(func.max(PriceChangeLog.id)))).scalar()
    return unit, promo, conv, change


async def test_lecturas_del_agente_de_b(session, other_session):
    unit_a, *_ = await _seed(session, "A", "100")
    await _seed(other_session, "B", "200")
    for name in ("get_calendar", "get_history", "get_offer_promotions"):
        res = await tools.exec_read(
            other_session, name,
            {"unit_type_id": unit_a.id, "date_from": str(D1), "date_to": str(D1)},
        )
        assert res == {"error": f"la unidad {unit_a.id} no existe"}, name
    ctx = await orchestrator._units_context(other_session)
    assert "A-3BR" not in ctx and "B-3BR" in ctx
    rng = {"date_from": str(D1 - timedelta(days=30)), "date_to": str(D1 + timedelta(days=30))}
    refs_a = [b["external_ref"] for b in await tools.exec_read(session, "get_bookings", rng)]
    refs_b = [b["external_ref"] for b in await tools.exec_read(other_session, "get_bookings", rng)]
    assert refs_a == ["bk-A"] and refs_b == ["bk-B"]


async def test_propuestas_del_agente_de_b_sobre_a(session, other_session):
    unit_a, promo_a, conv_a, change_a = await _seed(session, "A", "100")
    await _seed(other_session, "B", "200")
    cases = [
        ("propose_set_day", {"unit_type_id": unit_a.id, "day": str(D1), "price": 350000}),
        ("propose_set_range", {"unit_type_id": unit_a.id, "date_from": str(D1),
                               "date_to": str(D1), "price": 350000}),
        ("propose_block_availability", {"unit_type_id": unit_a.id, "date_from": str(D1),
                                        "date_to": str(D1)}),
        ("propose_delete_promotion", {"promotion_id": promo_a.id}),
        ("propose_retire_offer_promotion", {"promotion_id": promo_a.id}),
        ("propose_rollback", {"change_id": change_a}),
    ]
    for name, args in cases:
        with pytest.raises(ValueError, match="no existe"):
            await tools.build_proposal(other_session, name, args)
    # La propuesta pendiente de la conversación de A no existe para B.
    assert await orchestrator._pending_action(other_session, conv_a.id) is None
