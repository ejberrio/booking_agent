"""Pruebas de las herramientas del agente para promociones vía oferta (feature 011)."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.channels.base import FixedPriceWriteResult, RemoteRate
from app.core.config import settings
from app.models.agent import AgentAction
from app.models.property import Property, UnitType
from app.agent import tools
from app.services import offer_promotion_service as svc

pytestmark = pytest.mark.anyio

F = date.today() + timedelta(days=45)
L = F + timedelta(days=10)


class FakeCM:
    def __init__(self):
        self.written = []

    async def get_rates(self, room, df, dt):
        return [RemoteRate(room, df, D("350000"), 1)]

    async def set_fixed_price(self, fp):
        self.written.append(fp)
        return FixedPriceWriteResult(ok=True, verified=True, external_id=55123)

    async def disable_fixed_price(self, external_id, room):
        return FixedPriceWriteResult(ok=True, verified=True, external_id=external_id)


@pytest.fixture(autouse=True)
def _designate_offer(monkeypatch):
    monkeypatch.setattr(settings, "beds24_promo_offer_id", 3)


async def _unit(session):
    prop = Property(name="Casa")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="697411")
    session.add(unit)
    await session.flush()
    return unit


async def test_build_proposal_offer_promotion(session):
    unit = await _unit(session)
    prop = await tools.build_proposal(
        session,
        "propose_offer_promotion",
        {
            "unit_type_id": unit.id,
            "name": "Vacaciones",
            "first_night": F.isoformat(),
            "last_night": L.isoformat(),
            "discount_pct": 20,
            "min_nights": 3,
        },
    )
    assert "Vacaciones" in prop.summary and "20%" in prop.summary


async def test_build_proposal_rejects_invalid(session):
    unit = await _unit(session)
    base = {
        "unit_type_id": unit.id, "name": "X",
        "first_night": F.isoformat(), "last_night": L.isoformat(),
    }
    # sin descuento
    with pytest.raises(ValueError):
        await tools.build_proposal(session, "propose_offer_promotion", base)
    # pct fuera de rango
    with pytest.raises(ValueError):
        await tools.build_proposal(session, "propose_offer_promotion", {**base, "discount_pct": 150})
    # precio <= 0
    with pytest.raises(ValueError):
        await tools.build_proposal(session, "propose_offer_promotion", {**base, "price": 0})
    # fechas en el pasado
    with pytest.raises(ValueError):
        await tools.build_proposal(
            session,
            "propose_offer_promotion",
            {**base, "first_night": "2020-01-01", "last_night": "2020-01-05", "price": 100},
        )


async def test_apply_proposal_creates_and_publishes(session):
    unit = await _unit(session)
    cm = FakeCM()
    action = AgentAction(
        tool="propose_offer_promotion",
        arguments={
            "unit_type_id": unit.id, "name": "Vacaciones",
            "first_night": F.isoformat(), "last_night": L.isoformat(),
            "discount_pct": 20, "min_nights": 3,
        },
        fingerprint=None,
    )
    outcome = await tools.apply_proposal(session, cm, action, message_id=None)
    assert outcome.status == "applied"
    assert cm.written and cm.written[0].price == D("280000")
    promos = await svc.list_promotions(session, unit.id)
    assert len(promos) == 1 and promos[0].status == "published"


async def test_get_offer_promotions_read(session):
    unit = await _unit(session)
    cm = FakeCM()
    prev = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"),
    )
    await svc.apply(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"), fingerprint=prev.fingerprint,
    )
    out = await tools.exec_read(session, "get_offer_promotions", {"unit_type_id": unit.id})
    assert out[0]["name"] == "Vacaciones" and out[0]["price"] == "280000"


async def test_apply_proposal_retire(session):
    unit = await _unit(session)
    cm = FakeCM()
    prev = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"),
    )
    res = await svc.apply(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"), fingerprint=prev.fingerprint,
    )
    action = AgentAction(
        tool="propose_retire_offer_promotion",
        arguments={"promotion_id": res.id},
        fingerprint=None,
    )
    outcome = await tools.apply_proposal(session, cm, action, message_id=None)
    assert outcome.status == "applied"
    promos = await svc.list_promotions(session, unit.id)
    assert promos[0].status == "retired"
