"""Feature 018: motor v2 — agrupación por rango, supersede, exclusiones, racional."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.market.provider import MarketSnapshot
from app.models.calendar import CalendarDay
from app.models.enums import ChannelKind, EventKind, Relevance, SuggestionStatus
from app.models.market import Event, PriceSuggestion
from app.models.property import Channel, Property, UnitType
from app.services import pricing_service, suggestion_engine

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date(2026, 9, 1)  # "hoy" inyectado: el motor no depende del reloj en tests
E1, E3 = date(2026, 9, 10), date(2026, 9, 12)


class FakeMarket:
    def __init__(self, adr=None, samples=5):
        self.adr = adr
        self.samples = samples
        self.calls: list = []

    async def get_snapshot(self, zone, month):
        self.calls.append((zone, month))
        if self.adr is None:
            return None
        return MarketSnapshot(
            zone=zone, month=month, adr=D(self.adr), occupancy_pct=None,
            sample_size=self.samples, source="tavily",
        )


async def _seed(session, *, days=30, base="300000"):
    prop = Property(name="Apto", city="Sabaneta", external_ref="337229")
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


def _event(name="Concierto inaugural", start=E1, end=E3, rel=Relevance.high):
    return Event(
        name=name, start_date=start, end_date=end, kind=EventKind.concert,
        relevance=rel, location="Daviarena", source_url="https://x.co/e",
        dedup_key=f"{name}|{start}",
    )


async def _generate(session, unit, market=None):
    return await suggestion_engine.generate_suggestions(
        session,
        unit_type_id=unit.id,
        date_from=TODAY,
        date_to=TODAY + timedelta(days=29),
        market=market,
        today=TODAY,
    )


async def test_evento_multidia_una_sugerencia_de_rango(session):
    prop, unit = await _seed(session)
    session.add(_event())
    await session.flush()
    sugs = await _generate(session, unit)
    ev_sugs = [s for s in sugs if s.date_from == E1]
    assert len(ev_sugs) == 1
    s = ev_sugs[0]
    assert (s.date_from, s.date_to) == (E1, E3)
    assert s.suggested_price == D("390000")  # +30%
    ev_factor = next(f for f in s.rationale["factors"] if f["kind"] == "event")
    assert ev_factor["event"]["name"] == "Concierto inaugural"
    assert ev_factor["event"]["location"] == "Daviarena"
    assert ev_factor["event"]["source_url"] == "https://x.co/e"
    assert s.rationale["text"]  # compatibilidad v1


async def test_corte_por_cambio_de_precio_base(session):
    prop, unit = await _seed(session)
    await pricing_service.set_base_price(
        session, unit_type_id=unit.id, day=date(2026, 9, 11), new_price=D("350000")
    )
    session.add(_event())
    await session.flush()
    sugs = [s for s in await _generate(session, unit) if s.date_from >= E1 and s.date_to <= E3]
    assert len(sugs) == 3  # 10 (300k), 11 (350k), 12 (300k)
    assert {s.suggested_price for s in sugs} == {D("390000"), D("455000")}


async def test_reservas_excluidas(session):
    prop, unit = await _seed(session)
    session.add(_event())
    session.add(CalendarDay(unit_type_id=unit.id, date=date(2026, 9, 11), units_available=0))
    await session.flush()
    covered: set[date] = set()
    for s in await _generate(session, unit):
        d = s.date_from
        while d <= s.date_to:
            covered.add(d)
            d += timedelta(days=1)
    assert date(2026, 9, 11) not in covered
    assert {date(2026, 9, 10), date(2026, 9, 12)} <= covered


async def test_hueco_proximo_sugiere_bajar(session):
    prop, unit = await _seed(session)  # sin eventos, sin ocupación
    sugs = await _generate(session, unit)
    assert sugs, "debe sugerir descuento para huecos próximos"
    for s in sugs:
        assert s.date_to <= TODAY + timedelta(days=14)  # fuera de la ventana no hay señal
        assert D("255000") <= s.suggested_price < D("300000")  # descuento con tope −15%
        assert any(f["kind"] == "gap" for f in s.rationale["factors"])


async def test_supersede_solapada_y_equivalente(session):
    prop, unit = await _seed(session)
    session.add(_event(rel=Relevance.medium))
    await session.flush()
    first = await _generate(session, unit)
    ev_first = next(s for s in first if s.date_from == E1)

    # segundo scan con señal distinta (aparece un evento high) → supersede y crea nueva
    session.add(_event(name="Concierto XL", rel=Relevance.high))
    await session.flush()
    second = await _generate(session, unit)
    await session.refresh(ev_first)
    assert ev_first.status is SuggestionStatus.superseded
    assert any(s.date_from == E1 and s.suggested_price == D("390000") for s in second)

    # tercer scan sin cambios: equivalente exacta → no crea nada nuevo en el rango
    third = await _generate(session, unit)
    assert [s for s in third if s.date_from == E1] == []


async def test_housekeeping_vencidas_y_resueltas_intactas(session):
    prop, unit = await _seed(session)
    vencida = PriceSuggestion(
        property_id=prop.id, unit_type_id=unit.id,
        date_from=TODAY - timedelta(days=5), date_to=TODAY - timedelta(days=3),
        suggested_price=D("400000"), status=SuggestionStatus.proposed,
    )
    aplicada = PriceSuggestion(
        property_id=prop.id, unit_type_id=unit.id,
        date_from=E1, date_to=E3,
        suggested_price=D("999999"), status=SuggestionStatus.applied,
    )
    session.add_all([vencida, aplicada])
    await session.flush()
    await _generate(session, unit)
    await session.refresh(vencida)
    await session.refresh(aplicada)
    assert vencida.status is SuggestionStatus.superseded
    assert aplicada.status is SuggestionStatus.applied  # las resueltas no se tocan


async def test_mercado_ancla_y_snapshot_por_mes(session):
    prop, unit = await _seed(session)
    session.add(_event(rel=Relevance.medium))
    await session.flush()
    market = FakeMarket(adr="310000")
    sugs = await _generate(session, unit, market=market)
    s = next(x for x in sugs if x.date_from == E1)
    assert s.rationale["market"] == {"adr": "310000", "samples": 5, "source": "tavily"}
    assert any(f["kind"] == "market" for f in s.rationale["factors"])
    assert len(market.calls) >= 1  # un snapshot por mes del horizonte
    assert "Sabaneta" in market.calls[0][0]


async def test_sin_mercado_sin_factor(session):
    prop, unit = await _seed(session)
    session.add(_event())
    await session.flush()
    sugs = await _generate(session, unit, market=FakeMarket(adr=None))
    s = next(x for x in sugs if x.date_from == E1)
    assert "market" not in s.rationale
    assert all(f["kind"] != "market" for f in s.rationale["factors"])
