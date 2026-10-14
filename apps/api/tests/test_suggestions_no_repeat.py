"""Fix "sugerencias repetidas": lo ya aplicado o rechazado no vuelve a aparecer en el
scan siguiente, salvo un cambio drástico (y entonces se avisa qué se decidió antes)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import app.api.routes.suggestions as suggestion_routes
from app.channels.base import WriteResult
from app.core.config import settings
from app.domain import suggestion_repeat as repeat
from app.market.provider import MarketSnapshot
from app.models.enums import ChannelKind, EventKind, Relevance, SuggestionStatus
from app.models.market import Event, PriceSuggestion
from app.models.property import Channel, Property, UnitType
from app.services import intelligence_service, pricing_service, suggestion_batch, suggestion_engine

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date.today()
E1, E3 = TODAY + timedelta(days=20), TODAY + timedelta(days=22)  # fuera de la ventana de hueco


class FakeCM:
    async def set_rate_range(self, room, df, dt, price):
        return WriteResult(True, True)

    async def aclose(self):
        return None


class FakeMarket:
    def __init__(self, adr: str):
        self.adr = D(adr)

    async def get_snapshot(self, zone, month):
        return MarketSnapshot(
            zone=zone, month=month, adr=self.adr, occupancy_pct=None, sample_size=5, source="tavily"
        )


async def _seed(session, *, city="Sabaneta", days=30, base="300000", ref="337229"):
    prop = Property(name="Apto", city=city, external_ref=ref)
    session.add(prop)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    for i in range(days):
        await pricing_service.set_base_price(
            session, unit_type_id=unit.id, day=TODAY + timedelta(days=i), new_price=D(base)
        )
    await session.flush()
    return prop, unit


async def _event(session, rel=Relevance.high, city="sabaneta") -> Event:
    ev = Event(
        name="Concierto inaugural", start_date=E1, end_date=E3, kind=EventKind.concert,
        relevance=rel, location="Daviarena", dedup_key=f"concierto|{E1}", city=city,
    )
    session.add(ev)
    await session.flush()
    return ev


async def _generate(session, unit, *, today=TODAY, market=None):
    return await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit.id, date_from=today, date_to=TODAY + timedelta(days=29),
        market=market, today=today,
    )


def _in_event(sugs):
    return [s for s in sugs if s.date_from <= E3 and s.date_to >= E1]


async def _pending_in_event(session, unit):
    res = await session.execute(
        select(PriceSuggestion).where(
            PriceSuggestion.unit_type_id == unit.id,
            PriceSuggestion.status.in_((SuggestionStatus.proposed, SuggestionStatus.approved)),
            PriceSuggestion.date_from <= E3,
            PriceSuggestion.date_to >= E1,
        )
    )
    return list(res.scalars())


async def _apply(session, sug):
    """Aplica como en la web: vista previa del lote + confirmación."""
    p = await suggestion_batch.preview_batch(session, [sug.id], today=TODAY)
    r = await suggestion_batch.apply_batch(session, FakeCM(), [sug.id], p.fingerprint, today=TODAY)
    assert r.suggestions == {sug.id: "applied"}


# --- aplicada: no se repite ---------------------------------------------------------


async def test_aplicada_no_se_vuelve_a_proponer(session):
    prop, unit = await _seed(session)
    await _event(session)
    [sug] = _in_event(await _generate(session, unit))
    assert sug.suggested_price == D("390000")  # +30 %
    await _apply(session, sug)
    assert await pricing_service.get_price(session, unit.id, E1) == D("390000")

    # Scan del día siguiente: antes recalculaba sobre 390.000 y proponía 507.000.
    again = await _generate(session, unit)
    assert _in_event(again) == []
    assert await _pending_in_event(session, unit) == []


async def test_aplicada_por_la_accion_unica_tampoco_se_repite(session):
    # Ruta "Aprobar y aplicar" (intelligence_service.apply_suggestion): la bitácora no
    # lleva suggestion_id, pero sí origen "suggestion" → mismo resultado.
    prop, unit = await _seed(session)
    await _event(session)
    [sug] = _in_event(await _generate(session, unit))
    await intelligence_service.apply_suggestion(session, FakeCM(), sug.id, today=TODAY)
    assert _in_event(await _generate(session, unit)) == []


async def test_cambio_drastico_se_repropone_con_la_decision_anterior(session):
    prop, unit = await _seed(session)
    ev = await _event(session, rel=Relevance.low)
    [sug] = _in_event(await _generate(session, unit))
    assert sug.suggested_price == D("315000")  # +5 %
    await _apply(session, sug)

    ev.relevance = Relevance.high  # el evento resultó grande: +30 % → 390.000 (+24 % vs 315.000)
    await session.flush()
    [nueva] = _in_event(await _generate(session, unit))
    # Se calcula sobre el precio del host (300.000), no sobre el ya subido (315.000 → 409.500).
    assert nueva.suggested_price == D("390000")
    prev = nueva.rationale["previous"]
    assert prev["status"] == "applied" and D(prev["price"]) == D("315000")
    assert prev["suggestion_id"] == sug.id
    assert (prev["date_from"], prev["date_to"]) == (E1.isoformat(), E3.isoformat())
    assert prev["decided_on"] and prev["threshold_pct"] == 15.0
    assert suggestion_routes._serialize(nueva)["previous"] == prev


async def test_cambio_pequeno_no_es_drastico(session):
    prop, unit = await _seed(session)
    ev = await _event(session, rel=Relevance.medium)
    [sug] = _in_event(await _generate(session, unit))
    assert sug.suggested_price == D("345000")  # +15 %
    await _apply(session, sug)

    ev.relevance = Relevance.high  # 390.000 vs 345.000 = +13 % < 15 %
    await session.flush()
    assert _in_event(await _generate(session, unit)) == []


async def test_umbral_configurable(session, monkeypatch):
    monkeypatch.setattr(settings, "suggestion_repeat_threshold_pct", 10.0)
    prop, unit = await _seed(session)
    ev = await _event(session, rel=Relevance.medium)
    [sug] = _in_event(await _generate(session, unit))
    await _apply(session, sug)
    ev.relevance = Relevance.high  # +13 % > 10 %
    await session.flush()
    [nueva] = _in_event(await _generate(session, unit))
    assert nueva.rationale["previous"]["threshold_pct"] == 10.0


async def test_bajada_aplicada_como_promocion_no_se_repite_a_diario(session):
    # "Libre próximo": el descuento crece 1 punto por día; aplicada la bajada (promoción,
    # el base no cambia), el scan de mañana no debe volver a proponerla.
    prop, unit = await _seed(session)
    first = await _generate(session, unit)
    d5 = TODAY + timedelta(days=5)
    sug = next(s for s in first if s.date_from <= d5 <= s.date_to)
    sug.status = SuggestionStatus.applied
    sug.applied_promotion_id = 1
    await session.flush()

    tomorrow = await _generate(session, unit, today=TODAY + timedelta(days=1))
    covered = {
        s.date_from + timedelta(days=i)
        for s in tomorrow
        for i in range((s.date_to - s.date_from).days + 1)
    }
    assert not (covered & {sug.date_from + timedelta(days=i) for i in range((sug.date_to - sug.date_from).days + 1)})


async def test_pendiente_repetida_de_antes_del_fix_se_retira(session):
    # Una pendiente idéntica a lo ya aplicado (creada antes del fix) desaparece en el scan.
    prop, unit = await _seed(session)
    await _event(session)
    [sug] = _in_event(await _generate(session, unit))
    await _apply(session, sug)
    repetida = PriceSuggestion(
        property_id=prop.id, unit_type_id=unit.id, date_from=E1, date_to=E3,
        suggested_price=D("390000"), status=SuggestionStatus.proposed,
        rationale={"text": "x", "factors": []},
    )
    session.add(repetida)
    await session.flush()
    await _generate(session, unit)
    await session.refresh(repetida)
    assert repetida.status is SuggestionStatus.superseded


# --- rechazada ------------------------------------------------------------------------


async def test_rechazada_no_se_repite_identica(session):
    prop, unit = await _seed(session)
    await _event(session)
    [sug] = _in_event(await _generate(session, unit))
    await intelligence_service.reject(session, sug.id)
    assert _in_event(await _generate(session, unit)) == []
    assert await _pending_in_event(session, unit) == []


async def test_rechazada_vuelve_si_el_cambio_es_drastico(session):
    prop, unit = await _seed(session)
    ev = await _event(session, rel=Relevance.low)
    [sug] = _in_event(await _generate(session, unit))
    await intelligence_service.reject(session, sug.id)
    ev.relevance = Relevance.high
    await session.flush()
    [nueva] = _in_event(await _generate(session, unit))
    assert nueva.suggested_price == D("390000")
    assert nueva.rationale["previous"]["status"] == "rejected"
    assert D(nueva.rationale["previous"]["price"]) == D("315000")


# --- precio actual ya igual al sugerido ----------------------------------------------


async def test_precio_actual_ya_igual_no_sugiere(session):
    # Hueco + mercado: target = (300.000·(1−d) + 318.000)/2. Con d entre 4 % y 8 % el
    # sugerido queda a ≤1 % del actual (tolerancia) → nada que sugerir esas noches.
    prop, unit = await _seed(session)
    sugs = await _generate(session, unit, market=FakeMarket("318000"))
    covered = {
        s.date_from + timedelta(days=i)
        for s in sugs
        for i in range((s.date_to - s.date_from).days + 1)
    }
    for ahead in (9, 10, 11, 12, 13):  # d = 8 %, 7 %, 6 %, 5 %, 4 %
        assert TODAY + timedelta(days=ahead) not in covered
    assert TODAY + timedelta(days=8) in covered  # d = 9 % → 295.500 (−1,5 %)
    for s in sugs:
        assert abs(s.suggested_price - D("300000")) > D("3000")


# --- aislamiento por cuenta (principio VI) -------------------------------------------


async def test_decisiones_de_otra_cuenta_no_cuentan(session, other_session):
    # A aplicó la sugerencia del evento; B (misma ciudad, mismas fechas) sí la recibe.
    prop_a, unit_a = await _seed(session)
    await _event(session)
    [sug_a] = _in_event(await _generate(session, unit_a))
    await _apply(session, sug_a)
    await session.commit()

    prop_b, unit_b = await _seed(other_session, ref="999001")
    [sug_b] = _in_event(await _generate(other_session, unit_b))
    assert sug_b.suggested_price == D("390000") and "previous" not in sug_b.rationale
    # Las consultas nuevas pasan por el filtro de cuenta: B no ve nada de la unidad de A.
    assert await suggestion_engine._prior_decisions(other_session, unit_a.id, E1, E3) == {}
    assert await suggestion_engine._price_logs(other_session, unit_a.id, E1, E3) == {}
    assert set(await suggestion_engine._prior_decisions(session, unit_a.id, E1, E3)) == {
        E1, E1 + timedelta(days=1), E3
    }


# --- reglas puras ---------------------------------------------------------------------


def test_reference_base_deshace_solo_cadena_de_sugerencias():
    L = repeat.PriceLog
    logs = [L(D("150"), D("170"), True), L(D("130"), D("150"), True), L(D("100"), D("130"), False)]
    assert repeat.reference_base(D("170"), logs) == D("130")  # se corta en el cambio manual
    assert repeat.reference_base(D("175"), logs) == D("175")  # no encadena (cambio externo)
    assert repeat.reference_base(D("130"), [L(None, D("130"), True)]) == D("130")
    assert repeat.reference_base(D("100"), []) == D("100")


def test_drastico_por_umbral_o_cambio_de_sentido():
    t = D("15")
    assert not repeat.is_drastic(D("110"), D("105"), D("100"), t)
    assert repeat.is_drastic(D("130"), D("105"), D("100"), t)
    # se había rechazado una subida (110) y ahora toca bajar (97): no es "la misma"
    assert repeat.is_drastic(D("97"), D("110"), D("100"), t)
    assert repeat.should_propose(
        D("97"), current=D("100"), reference=D("100"), prior_price=D("110"),
        threshold_pct=t, tolerance_pct=D("1"),
    )
    assert not repeat.should_propose(
        D("100.5"), current=D("100"), reference=D("100"), prior_price=None,
        threshold_pct=t, tolerance_pct=D("1"),
    )
