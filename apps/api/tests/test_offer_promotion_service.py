"""Pruebas del servicio de promociones vía oferta (fixed price), feature 011."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.channels.base import FixedPriceWriteResult, RemoteRate
from app.core.config import settings
from app.models.property import Property, UnitType
from app.services import offer_promotion_service as svc
from app.services.offer_promotion_service import PromotionError

pytestmark = pytest.mark.anyio

F = date.today() + timedelta(days=60)
L = F + timedelta(days=10)


class FakeCM:
    def __init__(self, base=D("350000"), fail=False):
        self.base = base
        self.fail = fail
        self.written: list = []
        self.disabled: list = []

    async def get_rates(self, room, df, dt):
        return [RemoteRate(room, df, self.base, 1)]

    async def set_fixed_price(self, fp):
        if self.fail:
            return FixedPriceWriteResult(ok=False, verified=False, detail="rechazado")
        self.written.append(fp)
        return FixedPriceWriteResult(ok=True, verified=True, external_id=55123)

    async def disable_fixed_price(self, external_id, room):
        self.disabled.append(external_id)
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


async def test_preview_computes_discount_from_pct(session):
    unit = await _unit(session)
    cm = FakeCM(base=D("350000"))
    prev = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"),
    )
    assert prev.base_price == D("350000")
    assert prev.price == D("280000")  # 20% off
    assert prev.saving == D("70000")
    assert prev.fingerprint


async def test_apply_creates_publishes_and_audits(session):
    unit = await _unit(session)
    cm = FakeCM()
    prev = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"), min_nights=3,
    )
    res = await svc.apply(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("20"), min_nights=3, fingerprint=prev.fingerprint,
    )
    assert res.status == "published" and res.external_id == 55123
    assert cm.written and cm.written[0].price == D("280000")
    promos = await svc.list_promotions(session, unit.id)
    assert len(promos) == 1 and promos[0].status == "published"
    assert promos[0].saving == D("70000") and promos[0].min_nights == 3


async def test_apply_publish_failure_marks_sync_error(session):
    unit = await _unit(session)
    cm = FakeCM(fail=True)
    prev = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="X", price=D("300000"),
    )
    res = await svc.apply(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="X", price=D("300000"), fingerprint=prev.fingerprint,
    )
    assert res.status == "sync_error" and res.published is False
    promos = await svc.list_promotions(session, unit.id)
    assert promos[0].status == "sync_error"


@pytest.mark.parametrize(
    "kwargs, msg",
    [
        ({"price": D("0")}, "mayor que 0"),
        ({"price": D("400000")}, "no es menor"),  # base 350k
        ({"discount_pct": D("150")}, "entre 0% y 100%"),
    ],
)
async def test_validations_reject(session, kwargs, msg):
    unit = await _unit(session)
    cm = FakeCM(base=D("350000"))
    with pytest.raises(PromotionError) as exc:
        await svc.preview(
            session, cm, unit_type_id=unit.id, first_night=F, last_night=L, name="X", **kwargs
        )
    assert msg in str(exc.value)


async def test_past_and_inverted_dates_reject(session):
    unit = await _unit(session)
    cm = FakeCM()
    with pytest.raises(PromotionError):
        await svc.preview(
            session, cm, unit_type_id=unit.id, first_night=L, last_night=F, name="X", price=D("1"),
        )


async def test_offer_defaults_to_one_when_unset(session, monkeypatch):
    # Beds24 asigna offerId=1 pase lo que pase; sin config, el destino es 1.
    monkeypatch.setattr(settings, "beds24_promo_offer_id", None)
    unit = await _unit(session)
    cm = FakeCM()
    prev = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L, name="X", price=D("300000"),
    )
    assert prev.offer_id == 1


async def test_overlap_warns_and_requires_confirm(session):
    unit = await _unit(session)
    cm = FakeCM()
    p1 = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Uno", discount_pct=D("20"),
    )
    await svc.apply(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Uno", discount_pct=D("20"), fingerprint=p1.fingerprint,
    )
    # segunda promo que se solapa
    p2 = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Dos", discount_pct=D("10"),
    )
    assert any("solapa" in w for w in p2.warnings)
    with pytest.raises(PromotionError):  # sin confirm_overlap
        await svc.apply(
            session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
            name="Dos", discount_pct=D("10"), fingerprint=p2.fingerprint,
        )


async def test_retire_neutralizes_and_hides(session):
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
    ret = await svc.retire(session, cm, res.id, confirm=True)
    assert ret.status == "retired"
    assert cm.disabled == [55123]
    promos = await svc.list_promotions(session, unit.id)
    assert promos[0].status == "retired"


async def test_edit_modifies_same_external_id(session):
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
    # editar: bajar más el precio (nuevo preview con exclude_id)
    p2 = await svc.preview(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("30"), exclude_id=res.id,
    )
    res2 = await svc.apply(
        session, cm, unit_type_id=unit.id, first_night=F, last_night=L,
        name="Vacaciones", discount_pct=D("30"), fingerprint=p2.fingerprint, promotion_id=res.id,
    )
    assert res2.id == res.id
    assert cm.written[-1].external_id == 55123  # modifica el mismo fixed price
    promos = await svc.list_promotions(session, unit.id)
    assert len(promos) == 1 and promos[0].price == D("245000")  # 30% off de 350k
