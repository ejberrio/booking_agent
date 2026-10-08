"""Feature 022: las bajadas sugeridas se aplican como promoción (el base no cambia)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.channels.base import FixedPriceWriteResult, RemoteRate, WriteResult
from app.core.config import settings
from app.db.session import get_session
from app.main import app
from app.models.enums import ChannelKind, PromotionStatus, SuggestionStatus
from app.models.market import PriceSuggestion
from app.models.pricing import NativeDeal, PricingRule, Promotion
from app.models.property import Channel, Property, UnitType
from app.models.sync import SyncIssue
from app.services import pricing_service, suggestion_batch

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date.today()
BASE = D("270000")


def day(n: int) -> date:
    return TODAY + timedelta(days=n)


class FakeCM:
    """Canal falso: precios (rates), publicación de base y de fixed prices (promociones)."""

    def __init__(self, *, promo_fails: bool = False, base=BASE):
        self.promo_fails = promo_fails
        self.base = base
        self.fixed: list = []
        self.rates: list = []

    async def get_rates(self, room, df, dt):
        return [RemoteRate(room, df, self.base, 1)]

    async def set_rate_range(self, room, df, dt, price):
        self.rates.append((df, dt, price))
        return WriteResult(True, True)

    async def set_fixed_price(self, fp):
        if self.promo_fails:
            return FixedPriceWriteResult(ok=False, verified=False, detail="rechazado")
        self.fixed.append(fp)
        return FixedPriceWriteResult(ok=True, verified=True, external_id=9000 + len(self.fixed))

    async def aclose(self):
        return None


@pytest.fixture(autouse=True)
def _offer(monkeypatch):
    monkeypatch.setattr(settings, "beds24_promo_offer_id", 3)


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _seed(session, *, min_price: str | None = None, mobile: bool = True):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    await session.flush()
    for i in range(0, 40):
        await pricing_service.set_base_price(session, unit_type_id=unit.id, day=day(i), new_price=BASE)
    if min_price:
        session.add(PricingRule(property_id=prop.id, min_price=D(min_price), is_active=True))
    if mobile:
        session.add_all(
            [
                NativeDeal(channel=ChannelKind.airbnb, name="Mobile Only", discount_pct=D("10"), stacking="always"),
                NativeDeal(channel=ChannelKind.booking, name="Mobile rate", discount_pct=D("10"), stacking="always"),
                NativeDeal(channel=ChannelKind.airbnb, name="Descuento semanal", discount_pct=D("5"), stacking="conditional"),
            ]
        )
    await session.flush()
    return prop, unit


async def _sug(session, prop, unit, d1, d2, price, factors=None):
    s = PriceSuggestion(
        property_id=prop.id, unit_type_id=unit.id, date_from=d1, date_to=d2,
        suggested_price=D(price), status=SuggestionStatus.proposed,
        rationale={"text": "x", "factors": factors or [{"kind": "gap", "label": "libre"}]},
        confidence=D("0.7"),
    )
    session.add(s)
    await session.flush()
    return s


async def test_lote_mixto_subida_cambia_base_bajada_crea_promocion(session):
    prop, unit = await _seed(session)
    up = await _sug(session, prop, unit, day(10), day(10), "351000",
                    [{"kind": "event", "label": "x", "event": {"name": "Juanes"}}])
    down = await _sug(session, prop, unit, day(20), day(22), "240300")
    p = await suggestion_batch.preview_batch(session, [up.id, down.id], today=TODAY)
    modes = {(i.date, i.mode) for i in p.items if i.valid}
    assert (day(10), "base") in modes and (day(20), "promotion") in modes
    promo_item = next(i for i in p.items if i.date == day(20))
    assert promo_item.promo_price == D("240300") and promo_item.promo_pct == D("11.0")
    assert promo_item.final_by_channel == {"booking": D("216270"), "airbnb": D("216270")}
    assert [c["name"] for c in p.conditional_deals] == ["Descuento semanal"]

    cm = FakeCM()
    r = await suggestion_batch.apply_batch(session, cm, [up.id, down.id], p.fingerprint, today=TODAY)
    assert r.failed_count == 0 and r.applied_count == 4
    # subida: base cambia; bajada: base intacto y una promoción por el tramo
    assert await pricing_service.get_price(session, unit.id, day(10)) == D("351000")
    assert await pricing_service.get_price(session, unit.id, day(21)) == BASE
    assert len(cm.fixed) == 1 and cm.fixed[0].price == D("240300")
    assert (cm.fixed[0].first_night, cm.fixed[0].last_night) == (day(20), day(22))
    [promo] = (await session.execute(select(Promotion))).scalars().all()
    assert promo.name.startswith("StayLever · Libre próximo")
    assert promo.conditions["source"] == "suggestion" and promo.conditions["suggestion_ids"] == [down.id]
    await session.refresh(down)
    assert down.status is SuggestionStatus.applied and down.applied_promotion_id == promo.id
    assert r.promotions[0]["id"] == promo.id


async def test_recorte_por_minimo_y_omision(session):
    prop, unit = await _seed(session, min_price="230000")
    s = await _sug(session, prop, unit, day(5), day(5), "229500")  # −15 %
    p = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    [it] = p.items
    assert it.valid and it.clipped and it.promo_price == D("255556") and p.min_price == D("230000")
    # mínimo por encima del base → omitida
    rule = (await session.execute(select(PricingRule))).scalars().first()
    rule.min_price = D("280000")
    await session.flush()
    p2 = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    assert p2.items[0].valid is False and p2.items[0].reason == "por debajo del precio mínimo"
    assert p.fingerprint != p2.fingerprint  # cambiar el mínimo invalida la confirmación


async def test_tramos_por_precio_distinto(session):
    prop, unit = await _seed(session, mobile=False)
    a = await _sug(session, prop, unit, day(20), day(20), "248000")
    b = await _sug(session, prop, unit, day(21), day(22), "252000")
    p = await suggestion_batch.preview_batch(session, [a.id, b.id], today=TODAY)
    cm = FakeCM()
    await suggestion_batch.apply_batch(session, cm, [a.id, b.id], p.fingerprint, today=TODAY)
    assert [(f.first_night, f.last_night, f.price) for f in cm.fixed] == [
        (day(20), day(20), D("248000")),
        (day(21), day(22), D("252000")),
    ]


async def test_fallo_de_publicacion_no_deja_promocion(session):
    prop, unit = await _seed(session)
    s = await _sug(session, prop, unit, day(20), day(21), "240000")
    p = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    r = await suggestion_batch.apply_batch(session, FakeCM(promo_fails=True), [s.id], p.fingerprint, today=TODAY)
    assert r.failed_count == 2 and r.suggestions == {s.id: "pending"} and r.promotions == []
    assert (await session.execute(select(Promotion))).scalars().all() == []
    issues = (await session.execute(select(SyncIssue).where(SyncIssue.entity_ref.like("suggestion-promo:%")))).scalars().all()
    assert len(issues) == 1
    await session.refresh(s)
    assert s.status is SuggestionStatus.proposed


async def test_servicio_de_promociones_rechaza_tramo(session):
    # C1: Beds24 dice que el base es MENOR que el precio promo → PromotionError → tramo fallido.
    prop, unit = await _seed(session, mobile=False)
    s = await _sug(session, prop, unit, day(20), day(20), "250000")
    p = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    r = await suggestion_batch.apply_batch(session, FakeCM(base=D("200000")), [s.id], p.fingerprint, today=TODAY)
    assert r.failed_count == 1 and r.nights[0].reason.startswith("error al publicar")
    assert (await session.execute(select(Promotion))).scalars().all() == []


async def test_deal_fuera_de_fecha_no_cuenta_y_solapes(session):
    prop, unit = await _seed(session, mobile=False)
    session.add(NativeDeal(channel=ChannelKind.booking, name="Mobile julio", discount_pct=D("10"),
                           stacking="always", date_from=day(-60), date_to=day(-30)))
    session.add(Promotion(property_id=prop.id, unit_type_id=unit.id, name="Manual oct",
                          discount_type="percent", discount_value=D("10"), start_date=day(19),
                          end_date=day(25), status=PromotionStatus.active, conditions={}))
    await session.flush()
    s = await _sug(session, prop, unit, day(20), day(20), "240300")
    p = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    assert p.items[0].final_by_channel["booking"] == D("240300")  # el deal vencido no cuenta
    assert p.overlaps == ["Manual oct"]


async def test_min_price_endpoints(client, session):
    prop, unit = await _seed(session)
    await session.commit()
    assert (await client.get("/pricing/min-price")).json() == {"min_price": None}
    assert (await client.put("/pricing/min-price", json={"min_price": 230000})).json() == {"min_price": "230000.00"}
    assert (await client.get("/pricing/min-price")).json() == {"min_price": "230000.00"}
    assert (await client.put("/pricing/min-price", json={"min_price": 0})).status_code == 422
    assert (await client.put("/pricing/min-price", json={"min_price": None})).json() == {"min_price": None}


async def test_ofertas_marcan_origen_finalizada_y_sin_noches_libres(session):
    from app.models.booking import Booking
    from app.models.enums import BookingStatus
    from app.services import offer_promotion_service

    prop, unit = await _seed(session, mobile=False)
    s = await _sug(session, prop, unit, day(20), day(21), "240000")
    p = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    await suggestion_batch.apply_batch(session, FakeCM(), [s.id], p.fingerprint, today=TODAY)
    session.add(Promotion(property_id=prop.id, unit_type_id=unit.id, offer_id=3, name="Julio viejo",
                          discount_type="percent", discount_value=D("20"), start_date=day(-90),
                          end_date=day(-60), status=PromotionStatus.active, conditions={"published": True}))
    await session.flush()
    views = {v.name: v for v in await offer_promotion_service.list_promotions(session, unit.id)}
    sug_view = next(v for n, v in views.items() if n.startswith("StayLever"))
    assert sug_view.source == "suggestion" and not sug_view.finished and not sug_view.no_free_nights
    assert views["Julio viejo"].finished is True and views["Julio viejo"].source == "manual"
    # se reservan todas sus noches → "sin noches libres"
    session.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking, check_in=day(20),
                        check_out=day(22), status=BookingStatus.confirmed))
    await session.flush()
    sug_view = next(v for v in await offer_promotion_service.list_promotions(session, unit.id)
                    if v.name.startswith("StayLever"))
    assert sug_view.no_free_nights is True


async def test_endpoint_antiguo_rechaza_bajadas(session):
    from app.services import intelligence_service
    from app.services.intelligence_service import SuggestionStateError

    prop, unit = await _seed(session)
    s = await _sug(session, prop, unit, day(5), day(5), "240000")
    with pytest.raises(SuggestionStateError):
        await intelligence_service.apply_suggestion(session, FakeCM(), s.id)
    assert await pricing_service.get_price(session, unit.id, day(5)) == BASE
