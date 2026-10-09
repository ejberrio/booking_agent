"""Feature 025: avisos al celular (teléfonos, deduplicación, reservas, sugerencias, FCM)."""

from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from sqlalchemy import func, select

from app.channels.base import RemoteBooking, RemoteProperty, RemoteRate, RemoteRoom
from app.db.session import get_session
from app.main import app
from app.models.preference import AppPreference
from app.models.push import PushDevice, PushNotificationLog
from app.push.base import PushMessage, PushResult
from app.push.fcm import FcmSender
from app.services import push_service, sync_service, webhook_service

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date.today()
CI, CO = TODAY + timedelta(days=10), TODAY + timedelta(days=13)
GUEST = "Huesped Centinela"


class FakeSender:
    def __init__(self, invalid: set[str] | None = None):
        self.sent: list[PushMessage] = []
        self.invalid = invalid or set()

    async def send(self, message: PushMessage) -> PushResult:
        if message.token in self.invalid:
            return PushResult("invalid_token", "el teléfono ya no está registrado")
        self.sent.append(message)
        return PushResult("ok")

    async def aclose(self):
        return None


class FakeCM:
    def __init__(self, bookings):
        self.bookings = bookings

    async def get_properties(self):
        return [RemoteProperty("337229", "Apto", "COP", [RemoteRoom("697411", "3BR", 1)])]

    async def get_rates(self, room, df, dt):
        return [RemoteRate("697411", df, D("270000"), 1)]

    async def get_bookings(self, prop, since=None):
        return self.bookings

    async def aclose(self):
        return None


async def _count(session, model) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


# --------- teléfonos ---------


async def test_registro_upsert_reactiva_y_preferencias(session):
    d1 = await push_service.register_device(session, token="tok-aaaaaaaaaa", model="Pixel 8", app_version="1.0.0")
    d1.enabled = False
    d2 = await push_service.register_device(session, token="tok-aaaaaaaaaa", model="Pixel 8", app_version="1.0.1")
    assert d1.id == d2.id and d2.enabled and d2.app_version == "1.0.1"
    await push_service.update_device(session, d2.id, notify_suggestions=False)
    assert d2.notify_bookings and not d2.notify_suggestions
    with pytest.raises(LookupError):
        await push_service.update_device(session, 999, notify_bookings=False)


# --------- envío y deduplicación ---------


async def test_notify_deduplica_filtra_y_desactiva_token_invalido(session):
    a = await push_service.register_device(session, token="tok-aaaaaaaaaa")
    b = await push_service.register_device(session, token="tok-bbbbbbbbbb")
    c = await push_service.register_device(session, token="tok-cccccccccc")
    c.notify_bookings = False
    sender = FakeSender(invalid={"tok-bbbbbbbbbb"})
    kw = dict(kind="booking_new", ref="900", fingerprint="confirmed:x", title="T", body="B",
              url="/calendar", pref=push_service.PREF_BOOKINGS, sender=sender)
    assert await push_service.notify(session, **kw) == 1
    assert [m.token for m in sender.sent] == ["tok-aaaaaaaaaa"]  # c no quiere reservas
    assert b.enabled is False and a.enabled is True
    # mismo cambio → no se repite
    assert await push_service.notify(session, **kw) == 0 and len(sender.sent) == 1
    assert await _count(session, PushNotificationLog) == 1


async def test_sin_credenciales_no_envia_ni_marca(session, monkeypatch):
    await push_service.register_device(session, token="tok-aaaaaaaaaa")
    monkeypatch.setattr(push_service, "get_sender", lambda: None)
    n = await push_service.notify(session, kind="suggestions", ref="1", fingerprint="3", title="T",
                                  body="B", url="/suggestions", pref=push_service.PREF_SUGGESTIONS)
    assert n == 0 and await _count(session, PushNotificationLog) == 0
    assert (await push_service.send_test(session))["configured"] is False


# --------- reservas (sync entrante) ---------


async def test_eventos_de_reserva_y_un_solo_aviso_por_cambio(session):
    await push_service.register_device(session, token="tok-aaaaaaaaaa")
    sender = FakeSender()
    rb = RemoteBooking("900", "697411", CI, CO, channel="booking", guest_name=GUEST)
    past = RemoteBooking("100", "697411", TODAY - timedelta(days=30), TODAY - timedelta(days=28))

    async def sync(bookings):
        events: list = []
        await sync_service.import_remote(session, FakeCM(bookings), TODAY, TODAY + timedelta(days=30), events=events)
        await push_service.notify_booking_events(session, events, sender=sender)
        return events

    ev = await sync([rb, past])
    assert [(e.kind, e.ref) for e in ev] == [("new", "900")]  # la reserva pasada no avisa
    assert sender.sent[0].data == {"url": f"/calendar?month={CI:%Y-%m}"}
    assert "Booking.com" in sender.sent[0].body and GUEST not in sender.sent[0].body + sender.sent[0].title

    assert await sync([rb, past]) == [] and len(sender.sent) == 1  # sin cambios → nada

    # solo cambia el nombre/canal → no avisa
    rb2 = RemoteBooking("900", "697411", CI, CO, channel="airbnb", guest_name="Otro")
    assert await sync([rb2]) == []

    # fechas cambiadas → modificada
    rb3 = RemoteBooking("900", "697411", CI, CO + timedelta(days=1), channel="airbnb")
    assert [e.kind for e in await sync([rb3])] == ["modified"]
    # cancelada
    rb4 = RemoteBooking("900", "697411", CI, CO + timedelta(days=1), status="cancelled", channel="airbnb")
    assert [e.kind for e in await sync([rb4])] == ["cancelled"]
    assert [m.title for m in sender.sent] == ["Nueva reserva", "Reserva modificada", "Reserva cancelada"]


async def test_webhook_dispara_aviso(session, monkeypatch):
    from app.models.webhook import WebhookEvent  # noqa: F401

    await push_service.register_device(session, token="tok-aaaaaaaaaa")
    sender = FakeSender()
    monkeypatch.setattr(push_service, "get_sender", lambda: sender)
    body = json.dumps({"booking": {"id": 901, "propertyId": 337229, "arrival": CI.isoformat(),
                                   "departure": CO.isoformat(), "status": "confirmed"}}).encode()
    hint = webhook_service.parse_hint(body)
    await webhook_service.handle(session, FakeCM([RemoteBooking("901", "697411", CI, CO, channel="airbnb")]), hint)
    assert len(sender.sent) == 1 and sender.sent[0].body.startswith("Airbnb")


async def test_avisos_en_el_idioma_del_host(session):
    session.add(AppPreference(id=1, language="en"))
    await push_service.register_device(session, token="tok-aaaaaaaaaa")
    sender = FakeSender()
    await push_service.notify_suggestions(session, run_id=7, count=0, sender=sender)
    assert sender.sent == []
    await push_service.notify_suggestions(session, run_id=7, count=3, sender=sender)
    assert sender.sent[0].title == "Price suggestions" and sender.sent[0].body == "3 new suggestions to review"
    assert sender.sent[0].data == {"url": "/suggestions"}


# --------- adaptador FCM ---------


def _service_account() -> tuple[str, rsa.RSAPrivateKey]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    info = {"type": "service_account", "project_id": "staylever-test", "private_key": pem,
            "client_email": "push@staylever-test.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token"}
    return json.dumps(info), key


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


async def test_fcm_firma_jwt_envia_y_mapea_errores():
    raw, key = _service_account()
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "oauth2.googleapis.com":
            assertion = dict(x.split("=", 1) for x in request.content.decode().split("&"))["assertion"]
            head, claims, sig = assertion.split(".")
            key.public_key().verify(_b64d(sig), f"{head}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256())
            c = json.loads(_b64d(claims))
            assert c["scope"].endswith("firebase.messaging") and c["iss"].startswith("push@")
            return httpx.Response(200, json={"access_token": "ya29.test", "expires_in": 3600})
        if "bad" in request.content.decode():
            return httpx.Response(404, json={"error": {"status": "NOT_FOUND", "details": [{"errorCode": "UNREGISTERED"}]}})
        assert request.headers["Authorization"] == "Bearer ya29.test"
        body = json.loads(request.content)
        assert body["message"]["data"] == {"url": "/suggestions"}
        return httpx.Response(200, json={"name": "projects/staylever-test/messages/1"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sender = FcmSender(raw, client=client)
    ok = await sender.send(PushMessage("tok-good-1234", "T", "B", {"url": "/suggestions"}))
    bad = await sender.send(PushMessage("tok-bad-1234", "T", "B", {"url": "/suggestions"}))
    assert ok.status == "ok" and bad.status == "invalid_token"
    assert str(calls[1].url) == "https://fcm.googleapis.com/v1/projects/staylever-test/messages:send"
    assert sum(1 for c in calls if c.url.host == "oauth2.googleapis.com") == 1  # token en caché
    await client.aclose()


# --------- rutas ---------


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_rutas_de_telefonos(client, session, monkeypatch):
    monkeypatch.setattr(push_service, "get_sender", lambda: None)
    r = await client.post("/push/devices", json={"token": "tok-aaaaaaaaaa", "platform": "android", "model": "Pixel 8"})
    assert r.status_code == 200 and "token" not in r.json()
    dev_id = r.json()["id"]
    listed = (await client.get("/push/devices")).json()
    assert len(listed) == 1 and "token" not in listed[0]
    r = await client.patch(f"/push/devices/{dev_id}", json={"notify_bookings": False})
    assert r.json()["notify_bookings"] is False
    st = (await client.get("/push/status")).json()
    assert st["devices"] == 1 and st["configured"] in (True, False)
    assert (await client.post("/push/test")).json()["sent"] == 0
    assert (await client.delete(f"/push/devices/{dev_id}")).json() == {"deleted": True}
    assert (await client.delete(f"/push/devices/{dev_id}")).status_code == 404
    assert (await client.post("/push/devices", json={"token": "x"})).status_code == 422
    assert await _count(session, PushDevice) == 0
