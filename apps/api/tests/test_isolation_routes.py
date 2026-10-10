"""Feature 026 (principio VI): la cuenta B no ve ni modifica nada de la cuenta A por la API.

A = cuenta 1 (`session`), B = cuenta 2 (`other_session`). Todas las peticiones van como B
con identificadores de A: deben responder "no existe" (404) o listas sin datos de A, y el
adaptador del canal nunca se usa.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.context import RequestContext, current_identity
from app.db.session import get_session
from app.main import app
from app.models.agent import Conversation, Message
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarNote
from app.models.enums import (
    BookingStatus,
    ChangeOrigin,
    ChannelKind,
    MessageRole,
    PromotionType,
    SuggestionStatus,
)
from app.models.market import PointOfInterest, PriceSuggestion
from app.models.pricing import NativeDeal, Promotion
from app.models.property import Property, UnitType
from app.models.push import PushDevice
from app.services import pricing_service

pytestmark = pytest.mark.anyio

TODAY = date.today()
D1 = TODAY + timedelta(days=10)


class TouchedAdapter(AssertionError):
    pass


class NoAdapter:
    """Cualquier uso del adaptador del canal en estas pruebas es un fallo de aislamiento."""

    def __getattr__(self, name):
        if name == "aclose":
            async def _close():
                return None

            return _close
        raise TouchedAdapter(f"se usó el adaptador ({name}) con datos de otra cuenta")


async def _seed_a(session) -> dict:
    prop = Property(name="Casa A", city="Medellín", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="A-3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    for i in range(5):
        await pricing_service.set_base_price(
            session, unit_type_id=unit.id, day=D1 + timedelta(days=i),
            new_price=Decimal("300000"), origin=ChangeOrigin.manual,
        )
    session.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking, check_in=D1,
                        check_out=D1 + timedelta(days=2), status=BookingStatus.confirmed,
                        external_ref="900", guest_name="Huesped A"))
    sug = PriceSuggestion(property_id=prop.id, unit_type_id=unit.id, date_from=D1, date_to=D1,
                          suggested_price=Decimal("350000"), status=SuggestionStatus.proposed)
    promo = Promotion(property_id=prop.id, unit_type_id=unit.id, name="Promo A",
                      discount_type=PromotionType.percent, discount_value=Decimal("10"),
                      start_date=D1, end_date=D1)
    note = CalendarNote(unit_type_id=unit.id, date_from=D1, date_to=D1, text="nota A")
    conv = Conversation()
    poi = PointOfInterest(name="Estadio A")
    deal = NativeDeal(channel=ChannelKind.airbnb, name="Semanal A", discount_pct=Decimal("10"))
    dev = PushDevice(token="tok-A-aaaaaaaa")
    session.add_all([sug, promo, note, conv, poi, deal, dev])
    await session.flush()
    session.add(Message(conversation_id=conv.id, role=MessageRole.user, content="hola A"))
    await session.commit()
    change_id = (
        await session.execute(select(func.max(PriceChangeLog.id)))
    ).scalar()
    return {"unit": unit.id, "prop": prop.id, "sug": sug.id, "promo": promo.id, "note": note.id,
            "conv": conv.id, "poi": poi.id, "deal": deal.id, "dev": dev.id, "change": change_id}


@pytest_asyncio.fixture
async def as_b(session, other_session, monkeypatch):
    ids = await _seed_a(session)
    from app.api.routes import chat, pricing, suggestions, sync

    for mod in (pricing, suggestions, sync, chat):
        monkeypatch.setattr(mod, "get_adapter", lambda *_a, **_k: NoAdapter())

    async def _b_session():
        yield other_session

    async def _b_ctx():
        return RequestContext(account_id=2)

    app.dependency_overrides[get_session] = _b_session
    app.dependency_overrides[current_identity] = _b_ctx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, ids
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(current_identity, None)


async def test_lecturas_de_b_no_ven_a(as_b):
    client, ids = as_b
    u = ids["unit"]
    rng = f"date_from={D1}&date_to={D1 + timedelta(days=5)}"
    assert (await client.get("/units")).json() == []
    for path in (
        f"/pricing/calendar?unit_type_id={u}&{rng}",
        f"/pricing/kpis?unit_type_id={u}&{rng}",
        f"/pricing/history?unit_type_id={u}&{rng}",
        f"/pricing/promotions?unit_type_id={u}",
        f"/pricing/extension/status?unit_type_id={u}",
        f"/bookings?unit_type_id={u}&{rng}",
        f"/calendar-notes?unit_type_id={u}",
    ):
        r = await client.get(path)
        assert r.status_code == 404, (path, r.status_code, r.text)
    for path in ("/suggestions", "/chat/conversations", "/push/devices", "/pois",
                 "/pricing/native-deals", "/sync/issues"):
        r = await client.get(path)
        data = r.json()
        items = data if isinstance(data, list) else [v for v in data.values() if v]
        assert r.status_code == 200 and items == [], (path, r.text)
    r = await client.get(f"/chat/conversations/{ids['conv']}")
    assert r.status_code == 404
    assert (await client.get("/pricing/min-price")).json() == {"min_price": None}


async def test_escrituras_de_b_sobre_a_no_existen(as_b, session):
    client, ids = as_b
    u = ids["unit"]
    sel = {"date_from": str(D1), "date_to": str(D1)}
    posts = [
        ("/pricing/day", {"unit_type_id": u, "day": str(D1), "price": 1}),
        ("/pricing/range/preview", {"unit_type_id": u, "selection": sel, "price": 1}),
        ("/pricing/range/apply", {"unit_type_id": u, "selection": sel, "price": 1,
                                  "fingerprint": "x"}),
        ("/pricing/availability/preview", {"unit_type_id": u, "action": "block",
                                           "selection": sel}),
        ("/pricing/promotions/preview", {"unit_type_id": u, "name": "x", "first_night": str(D1),
                                         "last_night": str(D1), "price": 1}),
        ("/pricing/extension/preview", {"unit_type_id": u}),
        ("/calendar-notes", {"unit_type_id": u, "date_from": str(D1), "date_to": str(D1),
                             "text": "intruso"}),
        (f"/suggestions/{ids['sug']}/apply", {}),
        (f"/suggestions/{ids['sug']}/reject", {}),
        ("/pricing/rollback", {"change_id": ids["change"], "confirm": True}),
        ("/chat", {"message": "hola", "conversation_id": ids["conv"]}),
    ]
    for path, body in posts:
        r = await client.post(path, json=body)
        assert r.status_code in (404, 409), (path, r.status_code, r.text)
    for method, path, body in (
        ("PATCH", f"/calendar-notes/{ids['note']}", {"text": "x"}),
        ("DELETE", f"/calendar-notes/{ids['note']}", None),
        ("PATCH", f"/push/devices/{ids['dev']}", {"notify_bookings": False}),
        ("DELETE", f"/push/devices/{ids['dev']}", None),
        ("PATCH", f"/pois/{ids['poi']}", {"name": "x"}),
        ("DELETE", f"/pois/{ids['poi']}", None),
        ("PATCH", f"/pricing/native-deals/{ids['deal']}", {"name": "x"}),
        ("DELETE", f"/pricing/native-deals/{ids['deal']}", None),
        ("DELETE", f"/pricing/promotions/{ids['promo']}", None),
    ):
        r = await client.request(method, path, json=body)
        assert r.status_code == 404, (method, path, r.status_code, r.text)

    # Nada de A cambió.
    note = await session.get(CalendarNote, ids["note"])
    await session.refresh(note)
    assert note.text == "nota A"
    dev = await session.get(PushDevice, ids["dev"])
    await session.refresh(dev)
    assert dev.notify_bookings is True
    sug = await session.get(PriceSuggestion, ids["sug"])
    await session.refresh(sug)
    assert sug.status == SuggestionStatus.proposed
    assert (await session.execute(select(func.count()).select_from(CalendarNote))).scalar() == 1
