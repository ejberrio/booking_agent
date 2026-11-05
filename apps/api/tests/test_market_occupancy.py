"""Feature 043 (#185): demanda baja = tu ocupación baja Y un mes flojo en la zona."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

from app.domain.suggestion import MarketCap
from app.models.enums import EventKind, Relevance
from app.models.market import Event
from app.services import market_band_service as svc
from app.services.suggestion_engine import _cap_for

pytestmark = pytest.mark.anyio

CAP = MarketCap(p90=D("400000"), p75=D("300000"), p50=D("230000"), bedrooms=3)


def _ev(rel=Relevance.medium, kind=EventKind.concert):
    return Event(name="x", city="medellin", start_date=date(2026, 12, 4), kind=kind,
                 relevance=rel, dedup_key="x")


def test_mes_flojo_en_la_zona_baja_el_techo_y_lo_explica():
    cap = _cap_for(CAP, _ev(), low_demand=True, market_occ=D("17"))
    assert cap.level == "p75" and cap.p90 == D("300000") and cap.market_occ == D("17")


def test_mes_fuerte_en_la_zona_mantiene_el_p90_aunque_estes_vacio():
    assert _cap_for(CAP, _ev(), low_demand=True, market_occ=D("67.9")) is CAP


def test_sin_datos_del_mercado_se_comporta_como_la_039():
    assert _cap_for(CAP, _ev(), low_demand=True).level == "p75"
    assert _cap_for(CAP, _ev(Relevance.high), low_demand=True, market_occ=D("10")) is CAP
    assert _cap_for(CAP, _ev(), low_demand=False, market_occ=D("10")) is CAP


async def test_carga_por_zona_y_tamano(session):
    months = {1: 66.7, 2: 50, 3: 38.7, 4: 32.2, 5: 23.3, 6: 21.4, 7: 40.4, 8: 50,
              9: 17, 10: 32.3, 11: 52.5, 12: 67.9}
    assert await svc.import_occupancy(session, city="Sabaneta", bedrooms=3, months=months) == 12
    await svc.import_occupancy(session, city="Medellín", bedrooms=3, months={9: 18})  # reemplaza
    occ = await svc.occupancy_for(session, "Envigado", 3)  # toda el área usa Medellín
    assert occ[9] == D("18") and occ[12] == D("67.9") and len(occ) == 12
    assert await svc.occupancy_for(session, "Envigado", 2) == {}  # sin dato del tamaño ni "todas"
    summary = await svc.occupancy_summary(session)
    assert summary[0]["city"] == "medellin" and summary[0]["months"][1] == 66.7
    with pytest.raises(ValueError):
        await svc.import_occupancy(session, city="Medellín", bedrooms=3, months={13: 50})


async def test_motor_usa_la_ocupacion_del_mes(session, monkeypatch):
    from app.services import suggestion_engine

    seen = []
    orig = suggestion_engine._cap_for

    def spy(cap, ev, low, occ=None):
        seen.append(occ)
        return orig(cap, ev, low, occ)

    monkeypatch.setattr(suggestion_engine, "_cap_for", spy)
    from tests.test_suggestion_engine import TODAY, _generate, _seed

    prop, unit = await _seed(session, base="350000")
    unit.name = "Three-Bedroom Apartment"
    await svc.import_occupancy(session, city="Medellín", bedrooms=3, months={TODAY.month: 33})
    await _generate(session, unit)
    assert D("33") in seen
