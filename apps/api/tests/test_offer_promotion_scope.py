"""Feature 013 · US3: alcance de canales en promociones de precio (T016)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.models.property import Property, UnitType
from app.services import offer_promotion_service as svc
from app.services.offer_promotion_service import PromotionError
from tests.test_offer_promotion_service import FakeCM

pytestmark = pytest.mark.anyio

F = date.today() + timedelta(days=60)
L = F + timedelta(days=10)


async def _seed_unit(session) -> int:
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    return unit.id


async def test_preview_includes_scope(session):
    uid = await _seed_unit(session)
    prev = await svc.preview(
        session,
        FakeCM(),
        unit_type_id=uid,
        first_night=F,
        last_night=L,
        name="Promo B",
        discount_pct=D("10"),
        channels_scope=["booking"],
    )
    assert prev.channels_scope == ["booking"]


async def test_preview_without_scope_is_all_channels(session):
    uid = await _seed_unit(session)
    prev = await svc.preview(
        session, FakeCM(), unit_type_id=uid, first_night=F, last_night=L,
        name="Promo", discount_pct=D("10"),
    )
    assert prev.channels_scope is None


async def test_empty_scope_rejected(session):
    uid = await _seed_unit(session)
    with pytest.raises(PromotionError):
        await svc.preview(
            session, FakeCM(), unit_type_id=uid, first_night=F, last_night=L,
            name="Promo", discount_pct=D("10"), channels_scope=[],
        )


async def test_unknown_scope_token_rejected(session):
    uid = await _seed_unit(session)
    with pytest.raises(PromotionError):
        await svc.preview(
            session, FakeCM(), unit_type_id=uid, first_night=F, last_night=L,
            name="Promo", discount_pct=D("10"), channels_scope=["expedia"],
        )


async def test_apply_with_scope_disables_excluded_channels(session):
    uid = await _seed_unit(session)
    cm = FakeCM()
    res = await svc.apply(
        session, cm, unit_type_id=uid, first_night=F, last_night=L,
        name="Solo Booking", discount_pct=D("10"), channels_scope=["booking"],
    )
    assert res.status == "published"
    fp = cm.written[0]
    # Los canales gestionados EXCLUIDOS van en False; el incluido no se toca.
    assert fp.channels == {"airbnb": False}
    # Persistido en la promoción y visible en la lista.
    views = await svc.list_promotions(session, uid)
    assert views[0].channels_scope == ["booking"]


async def test_apply_without_scope_sends_no_channels(session):
    uid = await _seed_unit(session)
    cm = FakeCM()
    await svc.apply(
        session, cm, unit_type_id=uid, first_night=F, last_night=L,
        name="Todos", discount_pct=D("10"),
    )
    assert cm.written[0].channels is None
    views = await svc.list_promotions(session, uid)
    assert views[0].channels_scope is None


async def test_retire_intact_with_scoped_promotion(session):
    uid = await _seed_unit(session)
    cm = FakeCM()
    res = await svc.apply(
        session, cm, unit_type_id=uid, first_night=F, last_night=L,
        name="Solo Airbnb", discount_pct=D("10"), channels_scope=["airbnb"],
    )
    retired = await svc.retire(session, cm, res.id, confirm=True)
    assert retired.status in ("retired", "published", "sync_error") or retired.id == res.id
    views = await svc.list_promotions(session, uid)
    assert views[0].status == "retired"
    assert views[0].channels_scope == ["airbnb"]  # el alcance se conserva
