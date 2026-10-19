"""Feature 035: consultar y reportar eventos ("¿Falta un evento?")."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.agent.tools import exec_read
from app.llm.client import LLMResponse
from app.models.calendar import CalendarNote
from app.models.enums import EventKind, Relevance, SuggestionStatus
from app.models.market import Event, EventReport, PriceSuggestion
from app.models.property import Property, UnitType
from app.search.base import SearchResult
from app.services import event_report_service as svc
from app.services import event_service, pricing_service

pytestmark = pytest.mark.anyio

TODAY = date.today()
DAY = TODAY + timedelta(days=20)


class FakeSearch:
    def __init__(self):
        self.calls = []

    async def search(self, query, *, max_results=5, **opts):
        self.calls.append(query)
        return [SearchResult(title="Hebert Vargas en DAVIarena", content="4 de diciembre",
                             url="https://tuboleta.com/es/eventos/hebert")]


class FakeLLM:
    def __init__(self, items):
        self.items = items

    async def chat(self, *, messages, tools, model):
        return LLMResponse(content=json.dumps(self.items))


def _found(name="Hebert Vargas en concierto", day=DAY):
    return [{"name": name, "start_date": day.isoformat(), "end_date": None, "kind": "concert",
             "relevance": "medium", "location": "DAVIarena"}]


async def _prop(session, city="Medellín"):
    prop = Property(name="Apto", city=city, external_ref="x1")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="u1")
    session.add(unit)
    await session.flush()
    for i in range(40):
        await pricing_service.set_base_price(session, unit_type_id=unit.id,
                                             day=TODAY + timedelta(days=i), new_price=Decimal("300000"))
    return unit


async def test_consultar_eventos_del_area_y_festivos(session):
    await _prop(session)
    for name, city, kind in (("Concierto DAVIarena", "sabaneta", EventKind.concert),
                             ("Puente festivo: prueba", "colombia", EventKind.holiday),
                             ("Feria en Guatapé", "guatape", EventKind.fair)):
        await event_service.upsert_event(session, name=name, start_date=DAY, kind=kind,
                                         relevance=Relevance.medium, city=city)
    out = await svc.list_events(session, TODAY, TODAY + timedelta(days=60))
    names = {e["name"]: e["origin"] for e in out}
    assert names == {"Concierto DAVIarena": "búsqueda", "Puente festivo: prueba": "festivo"}
    via_tool = await exec_read(session, "get_events", {"date_from": TODAY.isoformat(),
                                                       "date_to": DAY.isoformat()})
    assert len(via_tool) == 2


async def test_ya_existe_no_gasta_busqueda(session):
    await _prop(session)
    await event_service.upsert_event(session, name="Hebert Vargas · Éxito tras Éxito",
                                     start_date=DAY, kind=EventKind.concert,
                                     relevance=Relevance.high, city="sabaneta")
    s = FakeSearch()
    res = await svc.report(session, name="Hebert Vargas", start_date=DAY, search=s,
                           llm=FakeLLM([]), today=TODAY)
    assert res.status == svc.EXISTS and s.calls == []
    assert await svc.reports_today(session) == 0  # no cuenta para el tope


async def test_confirmado_se_comparte_y_recalcula_sugerencias(session):
    unit = await _prop(session)
    res = await svc.report(session, name="Hebert Vargas", start_date=DAY, venue="DAVIarena",
                           search=FakeSearch(), llm=FakeLLM(_found()), today=TODAY)
    assert res.status == svc.VERIFIED
    ev = (await session.execute(select(Event))).scalar_one()
    # el recinto conocido fija municipio e importancia
    assert (ev.city, ev.relevance, ev.location) == ("sabaneta", Relevance.high, "DAVIarena")
    assert ev.source_url == "https://tuboleta.com/es/eventos/hebert"
    sug = (await session.execute(select(PriceSuggestion).where(
        PriceSuggestion.unit_type_id == unit.id, PriceSuggestion.date_from <= DAY,
        PriceSuggestion.date_to >= DAY))).scalars().all()
    assert sug and sug[0].status == SuggestionStatus.proposed
    assert sug[0].suggested_price == Decimal("390000")  # +30 %, sin aplicar nada
    out = await svc.list_events(session, DAY, DAY)
    assert out[0]["origin"] == "reportado por ti"


async def test_no_confirmado_queda_como_nota_privada(session):
    await _prop(session)
    res = await svc.report(session, name="Fiesta del barrio", start_date=DAY,
                           search=FakeSearch(), llm=FakeLLM([]), today=TODAY)
    assert res.status == svc.UNVERIFIED
    assert (await session.execute(select(Event))).first() is None
    note = (await session.execute(select(CalendarNote))).scalar_one()
    assert "Fiesta del barrio" in note.text and note.date_from == DAY


async def test_tope_diario_y_validaciones(session):
    await _prop(session)
    for i in range(svc.REPORTS_PER_DAY):
        await svc.report(session, name=f"Evento {i} raro", start_date=DAY, search=FakeSearch(),
                         llm=FakeLLM([]), today=TODAY)
    with pytest.raises(svc.ReportError):
        await svc.report(session, name="Uno más", start_date=DAY, search=FakeSearch(),
                         llm=FakeLLM([]), today=TODAY)
    for bad in (dict(name="xy", start_date=DAY),
                dict(name="Pasado", start_date=TODAY - timedelta(days=1)),
                dict(name="Largo", start_date=DAY, end_date=DAY + timedelta(days=40))):
        with pytest.raises(svc.ReportError):
            await svc.report(session, today=TODAY, **bad)
    assert len((await session.execute(select(EventReport))).scalars().all()) == 3


async def test_aislamiento_reportes_por_cuenta(session, other_session):
    await _prop(session)
    await svc.report(session, name="Fiesta del barrio", start_date=DAY, search=FakeSearch(),
                     llm=FakeLLM([]), today=TODAY)
    assert (await other_session.execute(select(EventReport))).first() is None
    assert (await other_session.execute(select(CalendarNote))).first() is None
