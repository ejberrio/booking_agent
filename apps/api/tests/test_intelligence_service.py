from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.channels.base import WriteResult
from app.llm.client import LLMResponse
from app.market.reference import BaselineMarket
from app.models.audit import PriceChangeLog
from app.models.calendar import CalendarDay
from app.models.enums import (
    ChangeOrigin,
    ChannelKind,
    EventKind,
    Relevance,
    SuggestionStatus,
)
from app.models.intelligence import IntelligenceRun, MarketReference
from app.models.market import Event, PriceSuggestion
from app.models.property import Channel, Property, UnitType
from app.search.base import SearchResult
from app.services import intelligence_service, pricing_service, suggestion_engine

D = Decimal
DAY = date(2026, 8, 5)


class FakeSearch:
    def __init__(self, results=None):
        self.results = results or [SearchResult("Eventos", "Feria de las Flores en agosto")]

    async def search(self, query, *, max_results=5):
        return self.results


class FakeLLM:
    def __init__(self, content):
        self.content = content

    async def chat(self, *, messages, tools, model):
        return LLMResponse(content=self.content)


class FakeCM:
    def __init__(self):
        self.published: list = []

    async def set_rate(self, room, day, price):
        return await self.set_rate_range(room, day, day, price)

    async def set_rate_range(self, room, df, dt, price):
        self.published.append((room, df, dt, price))
        return WriteResult(True, True)


async def setup(session, *, occ0=False, event=False):
    prop = Property(name="Casa", city="Medellín")
    session.add(prop)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="r1")
    session.add(unit)
    await session.flush()
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=DAY, new_price=D("180000"))
    if occ0:
        session.add(CalendarDay(unit_type_id=unit.id, date=DAY, units_available=0))
    if event:
        session.add(
            Event(
                name="Feria de las Flores", start_date=DAY, end_date=DAY,
                kind=EventKind.festival, relevance=Relevance.high,
                dedup_key="feria|2026-08-05|medellin",
            )
        )
    await session.flush()
    return prop, unit


async def _count(session, model) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_generate_suggestion_for_event_without_market(session):
    prop, unit = await setup(session, occ0=True, event=True)
    sugs = await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit.id, date_from=DAY, date_to=DAY, market=None
    )
    assert len(sugs) == 1
    assert sugs[0].suggested_price > D("180000")
    assert "evento" in sugs[0].rationale["text"]


async def test_no_reproposal_of_equivalent(session):
    prop, unit = await setup(session, occ0=True, event=True)
    await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit.id, date_from=DAY, date_to=DAY, market=None
    )
    again = await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit.id, date_from=DAY, date_to=DAY, market=None
    )
    assert again == []
    assert await _count(session, PriceSuggestion) == 1


async def test_apply_suggestion_origin_and_publishes(session):
    prop, unit = await setup(session, occ0=True, event=True)
    sug = (
        await suggestion_engine.generate_suggestions(
            session, unit_type_id=unit.id, date_from=DAY, date_to=DAY, market=None
        )
    )[0]
    cm = FakeCM()
    applied = await intelligence_service.apply_suggestion(session, cm, sug.id)
    assert applied.status is SuggestionStatus.applied
    assert applied.applied_change_id is not None
    assert await pricing_service.get_price(session, unit.id, DAY) == sug.suggested_price
    log = (
        await session.execute(
            select(PriceChangeLog).where(PriceChangeLog.origin == ChangeOrigin.suggestion)
        )
    ).scalars().first()
    assert log is not None
    assert cm.published


async def test_scan_records_run_and_dedups(session):
    prop, unit = await setup(session)
    content = (
        '[{"name":"Feria","start_date":"2026-08-05","end_date":null,"kind":"festival",'
        '"relevance":"high","location":"Medellín"},'
        '{"name":"SinFecha","start_date":null,"kind":"other","relevance":"low"}]'
    )
    run = await intelligence_service.scan(
        session, FakeSearch(), FakeLLM(content), None,
        queries=["eventos medellin"], unit_type_id=unit.id, date_from=DAY, date_to=DAY,
    )
    assert run.events_found == 1  # el candidato sin fecha se descarta
    assert await _count(session, Event) == 1
    assert run.suggestions_created >= 1
    assert await _count(session, IntelligenceRun) == 1

    # segunda corrida: idempotente
    await intelligence_service.scan(
        session, FakeSearch(), FakeLLM(content), None,
        queries=["eventos medellin"], unit_type_id=unit.id, date_from=DAY, date_to=DAY,
    )
    assert await _count(session, Event) == 1  # sin duplicar


async def test_baseline_market_reference(session):
    session.add(MarketReference(zone="Medellín", reference_price=D("200000"), source="baseline"))
    await session.flush()
    bm = BaselineMarket(session)
    assert await bm.get("Medellín", DAY) == D("200000")
    assert await bm.get("Otra", DAY) is None
