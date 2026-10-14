"""Feature 029: modo sin conexión (apartamento a mano, iCal y aplicar a mano)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.agent.orchestrator import resolve_action, run_turn
from app.channels.factory import get_adapter, has_credentials, set_channel_mode
from app.channels.simulated import ManualChannelAdapter
from app.db.session import get_session
from app.llm.client import LLMResponse, ToolCall
from app.main import app
from app.models.account import Account
from app.models.agent import Conversation
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Channel, Property
from app.services import ical_service, manual_service, pricing_service
from app.services.manual_service import ManualError, ManualListing

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date(2026, 10, 14)  # miércoles
AIRBNB_ICAL = "https://www.airbnb.com.co/calendar/ical/12345.ics?s=abc"


def _ics(*events: tuple[str, date, date, str]) -> str:
    body = "".join(
        f"BEGIN:VEVENT\r\nDTSTART;VALUE=DATE:{s:%Y%m%d}\r\nDTEND;VALUE=DATE:{e:%Y%m%d}\r\n"
        f"UID:{uid}\r\nSUMMARY:{summary}\r\nEND:VEVENT\r\n"
        for uid, s, e, summary in events
    )
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\n{body}END:VCALENDAR\r\n"


def _transport(text: str):
    return httpx.MockTransport(lambda request: httpx.Response(200, text=text))


async def _create(session, **kw):
    return await manual_service.create_apartment(
        session, 1, name="Apto Laureles", city="Medellín", weekday_price=D("250000"),
        weekend_price=D("320000"),
        listings=[ManualListing(ChannelKind.airbnb, "https://www.airbnb.com.co/rooms/12345",
                                AIRBNB_ICAL)],
        today=TODAY, **kw,
    )


async def test_crear_apartamento_siembra_precios_y_modo(session):
    unit = await _create(session)
    rates = {r.date: r.base_price for r in (await session.execute(select(Rate))).scalars()}
    assert len(rates) == manual_service.SEED_DAYS
    assert rates[TODAY] == D("250000")  # miércoles
    assert rates[date(2026, 10, 16)] == D("320000")  # viernes
    assert rates[date(2026, 10, 17)] == D("320000")  # sábado
    assert rates[date(2026, 10, 18)] == D("250000")  # domingo
    # la siembra no llena el historial de cambios
    assert (await session.execute(select(func.count()).select_from(PriceChangeLog))).scalar_one() == 0
    assert (await session.get(Account, 1)).channel_mode == "manual"
    assert isinstance(get_adapter(session), ManualChannelAdapter) and has_credentials(session)
    ch = (await session.execute(select(Channel))).scalar_one()
    links = manual_service.calendar_links(ch)
    assert links["calendar_url"].endswith("/multicalendar/12345")
    over = await manual_service.overview(session)
    assert over[0]["unit_type_id"] == unit.id and over[0]["channels"][0]["has_ical"]
    assert "s=abc" not in str(over)  # el enlace iCal completo no se devuelve


async def test_validaciones(session):
    with pytest.raises(ManualError):
        await manual_service.create_apartment(
            session, 1, name="X", city="Y", weekday_price=D("1"),
            listings=[ManualListing(ChannelKind.airbnb, "http://inseguro", None)], today=TODAY,
        )
    # una cuenta conectada no pasa a manual
    session.add(Property(name="Beds24", provider="beds24", external_ref="337229"))
    await session.flush()
    with pytest.raises(ManualError):
        await _create(session)


def test_parser_ical_y_dominios_permitidos():
    text = _ics(("r1", date(2026, 10, 20), date(2026, 10, 23), "Reserved"),
                ("b1", date(2026, 11, 1), date(2026, 11, 3), "Airbnb (Not available)"))
    evs = ical_service.parse(text)
    assert [(e.uid, e.blocked) for e in evs] == [("r1", False), ("b1", True)]
    assert ical_service.allowed(AIRBNB_ICAL)
    assert ical_service.allowed("https://admin.booking.com/hotel/hoteladmin/ical.html?t=x")
    assert not ical_service.allowed("http://www.airbnb.com/x.ics")
    assert not ical_service.allowed("https://169.254.169.254/latest")
    assert not ical_service.allowed("https://evil.com/airbnb.com.ics")


async def test_sync_ical_reservas_bloqueos_y_cancelaciones(session):
    await _create(session)
    first = _ics(("r1", date(2026, 10, 20), date(2026, 10, 23), "Reserved"),
                 ("b1", date(2026, 11, 1), date(2026, 11, 3), "Airbnb (Not available)"))
    rep = await ical_service.sync_account(session, today=TODAY, transport=_transport(first))
    assert rep.bookings == 1 and rep.blocked_nights == 2 and not rep.errors
    b = (await session.execute(select(Booking))).scalar_one()
    assert b.channel_kind == ChannelKind.airbnb and b.guest_name is None
    blocked = (await session.execute(
        select(CalendarDay).where(CalendarDay.date == date(2026, 11, 1)))).scalar_one()
    assert blocked.is_blocked
    # la reserva desaparece del calendario → se cancela
    rep2 = await ical_service.sync_account(session, today=TODAY, transport=_transport(_ics()))
    assert rep2.cancelled == 1
    assert (await session.get(Booking, b.id)).status == BookingStatus.cancelled


async def test_error_ical_no_revela_el_enlace(session):
    await _create(session)
    bad = httpx.MockTransport(lambda request: httpx.Response(404))
    rep = await ical_service.sync_account(session, today=TODAY, transport=bad)
    assert rep.errors and "abc" not in rep.errors[0] and "airbnb" in rep.errors[0]


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    async def chat(self, *, messages, tools, model):
        return self.responses.pop(0)


async def test_asistente_registra_y_recuerda_aplicar_a_mano(session):
    unit = await _create(session, )
    day = date.today() + timedelta(days=10)
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=day, new_price=D("250000"))
    conv = Conversation(title="t")
    session.add(conv)
    await session.flush()
    llm = FakeLLM([LLMResponse(tool_calls=[ToolCall("c1", "propose_price_change", {
        "unit_type_id": unit.id, "mode": "percent", "value": 10, "dates": [day.isoformat()],
    })])])
    adapter = get_adapter(session)
    reply = await run_turn(session, adapter, llm, conversation_id=conv.id, user_text="sube 10%")
    done = await resolve_action(session, adapter, conversation_id=conv.id,
                                action_id=reply.pending_action_id, confirm=True)
    assert done.applied and "sin conexión" in done.text
    assert await pricing_service.get_price(session, unit.id, day) == D("275000")


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_rutas_crear_y_resumen(client, session, monkeypatch):
    async def _no_fetch(url, transport=None):
        return _ics()

    monkeypatch.setattr(ical_service, "fetch", _no_fetch)
    r = await client.post("/manual/apartments", json={
        "name": "Casa", "city": "Cartagena", "weekday_price": 300000,
        "airbnb_url": "https://www.airbnb.com/rooms/999", "airbnb_ical": AIRBNB_ICAL,
    })
    assert r.status_code == 200, r.text
    data = (await client.get("/manual")).json()
    assert data["channel_mode"] == "manual" and data["apartments"][0]["city"] == "Cartagena"
    assert (await client.get("/account")).json()["channel_mode"] == "manual"
    bad = await client.post("/manual/apartments", json={
        "name": "X", "city": "Y", "weekday_price": 1, "booking_ical": "ftp://x"})
    assert bad.status_code == 400


async def test_aislamiento_otra_cuenta_no_ve_los_apartamentos(session, other_session):
    await _create(session)
    await session.commit()
    set_channel_mode(other_session, None)
    assert await manual_service.overview(other_session) == []
