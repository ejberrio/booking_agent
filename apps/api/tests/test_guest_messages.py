"""Feature 045 (#186): mensajes de huéspedes — bandeja, hilo, envío, IA sin datos personales."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from app.llm.client import LLMResponse
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Property, UnitType
from app.services import messages_service as svc
from app.services import webhook_service

pytestmark = pytest.mark.anyio
TODAY = date.today()


@pytest.fixture(autouse=True)
def _clear_cache():
    svc._cache.clear()
    yield
    svc._cache.clear()


class FakeMsgs:
    def __init__(self, msgs):
        self.msgs = msgs
        self.sent, self.marked, self.calls = [], [], 0

    async def get_messages(self, *, booking_ids=None, max_age=90, unread_only=False, max_pages=5):
        self.calls += 1
        out = self.msgs
        if booking_ids:
            out = [m for m in out if str(m["bookingId"]) in {str(b) for b in booking_ids}]
        return [dict(m) for m in out]

    async def send_message(self, booking_id, text):
        self.sent.append((booking_id, text))

    async def mark_messages_read(self, booking_id):
        self.marked.append(booking_id)


async def _seed(session):
    prop = Property(name="Apto", city="Sabaneta", external_ref="p1")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR Mayorca", external_ref="u1")
    session.add(unit)
    await session.flush()
    for ref, kind, d in (("B1", ChannelKind.booking, 5), ("A2", ChannelKind.airbnb, 20),
                         ("D3", ChannelKind.direct, 30)):
        session.add(Booking(unit_type_id=unit.id, channel_kind=kind, check_in=TODAY + timedelta(days=d),
                            check_out=TODAY + timedelta(days=d + 2), status=BookingStatus.confirmed,
                            external_ref=ref, guest_name="Carolina Pérez"))
    await session.flush()


MSGS = [
    {"id": 1, "bookingId": 1, "source": "guest", "read": True, "time": "2026-11-01T10:00:00Z",
     "message": "Hola, gracias"},
    {"id": 2, "bookingId": "B1", "source": "guest", "read": False, "time": "2026-11-10T09:00:00Z",
     "message": "Hola, soy Carolina Pérez, ¿a qué hora es el check-in? Mi cel 300 123 4567, correo caro@mail.com"},
    {"id": 3, "bookingId": "A2", "source": "host", "read": True, "time": "2026-11-09T09:00:00Z",
     "message": "¡Bienvenidos!"},
    {"id": 4, "bookingId": "ZZ9", "source": "guest", "read": False, "time": "2026-11-10T11:00:00Z",
     "message": "reserva ajena"},
    {"id": 5, "bookingId": "B1", "source": "internalNote", "read": True, "time": "2026-11-10T09:30:00Z",
     "message": "nota interna"},
]


def test_anonimiza_antes_de_la_ia():
    t = svc.redact("Soy Carolina Pérez, cel +57 300 123 4567, caro@mail.com, doc 1037654321, "
                   "https://airbnb.com/x", ["Carolina Pérez"])
    for leak in ("Carolina", "Pérez", "300 123", "caro@mail", "1037654321", "airbnb.com"):
        assert leak not in t
    assert "[huésped]" in t and "[teléfono]" in t and "[correo]" in t and "[enlace]" in t


async def test_bandeja_no_leidas_primero_y_sin_reservas_ajenas(session):
    await _seed(session)
    a = FakeMsgs(MSGS)
    convs = await svc.inbox(session, a)
    assert [c["booking"] for c in convs] == ["B1", "A2"]  # ZZ9 no es de la cuenta; 1 no existe
    assert convs[0]["unread"] == 1 and convs[0]["unit"] == "3BR Mayorca"
    await svc.inbox(session, a)
    assert a.calls == 1  # caché de 60 s: no gasta créditos de Beds24


async def test_hilo_marca_leido_y_envio_valida_canal(session):
    await _seed(session)
    a = FakeMsgs(MSGS)
    t = await svc.thread(session, a, "B1")
    assert [m["source"] for m in t["messages"]] == ["guest", "internalNote"] and a.marked == ["B1"]
    assert t["can_reply"]
    await svc.send(session, a, "B1", "  El check-in es a las 3 pm.  ")
    assert a.sent == [("B1", "El check-in es a las 3 pm.")]
    with pytest.raises(svc.MessagesError):
        await svc.send(session, a, "D3", "hola")  # reserva directa: no se puede por OTA
    with pytest.raises(svc.MessagesError):
        await svc.send(session, a, "B1", "x" * (svc.MAX_TEXT + 1))
    with pytest.raises(LookupError):
        await svc.thread(session, a, "ZZ9")


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    async def chat(self, *, messages, tools, model):
        self.prompts.append(json.dumps(messages, ensure_ascii=False))
        return LLMResponse(content=self.reply)


async def test_sugerencia_sin_datos_personales_y_editable(session):
    await _seed(session)
    llm = FakeLLM("Hola Carolina, el check-in es desde las [hora de check-in]. Escríbeme a caro@mail.com")
    s = await svc.suggest(session, FakeMsgs(MSGS), llm, "B1", model="m")
    prompt = llm.prompts[0]
    for leak in ("Carolina", "Pérez", "300 123", "caro@mail.com"):
        assert leak not in prompt
    assert "[hora de check-in]" in s.text and "Carolina" not in s.text and "caro@mail" not in s.text
    with pytest.raises(svc.MessagesError):
        await svc.suggest(session, FakeMsgs([MSGS[2]]), llm, "A2", model="m")  # sin mensaje del huésped


async def test_webhook_detecta_mensajes_nuevos_sin_texto(session):
    raw = json.dumps({"booking": {"id": 77, "propertyId": 5},
                      "messages": [{"id": 9, "source": "guest", "read": False, "message": "secreto"},
                                   {"id": 10, "source": "host", "read": True, "message": "x"},
                                   {"id": 11, "source": "guest", "read": True, "message": "viejo"}]}).encode()
    hint = webhook_service.parse_hint(raw)
    assert hint.guest_message_ids == ("9",) and "secreto" not in repr(hint)
    assert webhook_service.parse_hint(b'{"booking": {"id": 1}}').guest_message_ids == ()


async def test_aislamiento_por_cuenta(session, other_session):
    await _seed(session)
    await session.commit()
    with pytest.raises(LookupError):
        await svc.thread(other_session, FakeMsgs(MSGS), "B1")
    assert await svc.inbox(other_session, FakeMsgs(MSGS)) == []
