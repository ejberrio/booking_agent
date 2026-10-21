"""Feature 038: techo de mercado (p90) para las sugerencias por evento."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.domain.suggestion import EventSignal, MarketCap, suggest_price_v2
from app.models.enums import Relevance
from app.models.market import MarketBand, PriceSuggestion
from app.models.property import UnitType
from app.services import market_band_service
from tests.test_suggestion_engine import E1, TODAY, _event, _generate, _seed

pytestmark = pytest.mark.anyio
D = Decimal


def test_habitaciones_desde_el_nombre():
    for name, n in (("Three-Bedroom Apartment", 3), ("Apto 3BR piscina", 3),
                    ("Casa 4 habitaciones", 4), ("Loft", None)):
        assert market_band_service.unit_bedrooms(UnitType(name=name)) == n
    assert market_band_service.unit_bedrooms(UnitType(name="Loft", bedrooms=2)) == 2


def test_evento_grande_no_pasa_del_p90_y_por_encima_se_sugiere_bajar():
    cap = MarketCap(p90=D("400000"), p75=D("300000"), bedrooms=3)
    ev = EventSignal(relevance=Relevance.high, name="Concierto")
    out = suggest_price_v2(D("350000"), event=ev, market_cap=cap)  # +30% = 455k → 400k
    assert out.price == D("400000") and any(f.kind == "market_cap" for f in out.factors)
    # ya por encima del p90 y sin evento: bajar, pero gradual (−15% máx.)
    out = suggest_price_v2(D("600000"), market_cap=cap)
    assert out.price == D("510000") and out.factors[-1].kind == "market_cap"
    # por debajo del p90 sin señales: nada que sugerir
    assert suggest_price_v2(D("250000"), market_cap=cap) is None
    # sin datos de mercado: igual que antes
    assert suggest_price_v2(D("350000"), event=ev).price == D("455000")


async def test_motor_usa_el_p90_de_la_zona_y_su_tamano(session):
    prop, unit = await _seed(session, base="350000")  # Sabaneta → zona Medellín
    unit.name = "Three-Bedroom Apartment"
    session.add(_event())
    n = await market_band_service.import_rows(
        session, city="Medellín", bedrooms=3,
        rows=[[(E1 + timedelta(days=i)).isoformat(), 160000, 230000, 300000, 400000]
              for i in range(-2, 5)])
    # otra zona y otro tamaño no cuentan
    session.add(MarketBand(city="medellin", bedrooms=1, day=E1, p90=D("150000")))
    session.add(MarketBand(city="cartagena", bedrooms=3, day=E1, p90=D("900000")))
    await session.flush()
    assert n == 7
    sugs = [s for s in await _generate(session, unit) if s.date_from == E1]
    assert sugs and sugs[0].suggested_price == D("400000")
    kinds = [f["kind"] for f in sugs[0].rationale["factors"]]
    assert "event" in kinds and "market_cap" in kinds
    summary = await market_band_service.summary(session, today=E1 - timedelta(days=2))
    assert any(b["city"] == "medellin" and b["bedrooms"] == 3 and b["days"] == 7 for b in summary)
    assert (await session.execute(select(PriceSuggestion))).scalars().first() is not None
    assert TODAY < E1


async def _bands(session):
    await market_band_service.import_rows(
        session, city="Medellín", bedrooms=3,
        rows=[[(E1 + timedelta(days=i)).isoformat(), 160000, 230000, 300000, 400000]
              for i in range(-2, 5)])


async def test_demanda_baja_eventos_medianos_topan_en_p75(session):
    prop, unit = await _seed(session, base="350000")
    unit.name = "Three-Bedroom Apartment"
    session.add(_event(rel=Relevance.medium))  # +15% = 402.5k
    await _bands(session)
    await session.flush()
    sug = next(s for s in await _generate(session, unit) if s.date_from == E1)
    cap = next(f for f in sug.rationale["factors"] if f["kind"] == "market_cap")
    assert sug.suggested_price == D("300000") and cap["level"] == "p75"


async def test_eventos_grandes_y_puentes_siguen_en_p90(session):
    from app.models.enums import EventKind

    prop, unit = await _seed(session, base="350000")
    unit.name = "Three-Bedroom Apartment"
    puente = _event(name="Puente festivo: prueba", rel=Relevance.medium)
    puente.kind = EventKind.holiday
    session.add(puente)
    await _bands(session)
    await session.flush()
    sug = next(s for s in await _generate(session, unit) if s.date_from == E1)
    assert sug.suggested_price == D("400000")  # +15% = 402.5k → p90


async def test_con_ocupacion_normal_el_techo_es_el_p90(session):
    from app.models.calendar import CalendarDay

    prop, unit = await _seed(session, base="350000")
    unit.name = "Three-Bedroom Apartment"
    session.add(_event(rel=Relevance.medium))
    for i in range(12):  # 12 de 30 noches ocupadas (40%): demanda normal
        session.add(CalendarDay(unit_type_id=unit.id, date=TODAY + timedelta(days=20 + i),
                                units_available=0))
    await _bands(session)
    await session.flush()
    sug = next(s for s in await _generate(session, unit) if s.date_from == E1)
    assert sug.suggested_price == D("400000")
