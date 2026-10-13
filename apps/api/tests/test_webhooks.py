"""Feature 020: avisos de reservas de Beds24 (autenticación, re-sync, robustez, estado)."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

import app.api.routes.hooks as hook_routes
from app.channels.base import RemoteBooking, RemoteProperty, RemoteRate, RemoteRoom, WriteResult
from app.channels.errors import ChannelError
from app.core.config import settings
from app.db.session import get_session
from app.main import app
from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, WebhookResult
from app.models.webhook import WebhookEvent
from app.services import secret_service as svc
from app.services import webhook_service

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date.today()
CI, CO = TODAY + timedelta(days=10), TODAY + timedelta(days=13)
KEY = "clave-de-prueba-1234"
GUEST = "Huesped Centinela"
TOKEN = "tok_STRIPE_CENTINELA"


class FakeCM:
    """Beds24 falso: estado vigente de las reservas + calendario; registra rangos y escrituras."""

    def __init__(self, bookings=None, *, fail=False):
        self.bookings = bookings or []
        self.fail = fail
        self.rate_ranges: list[tuple[date, date]] = []
        self.writes = 0

    async def get_properties(self):
        if self.fail:
            raise ChannelError("Token not valid")
        return [RemoteProperty("337229", "Apto", "COP", [RemoteRoom("697411", "3BR", 1)])]

    async def get_rates(self, room, df, dt):
        self.rate_ranges.append((df, dt))
        out, d = [], df
        while d <= dt:
            busy = any(
                b.status != "cancelled" and b.check_in <= d < b.check_out for b in self.bookings
            )
            out.append(RemoteRate("697411", d, D("270000"), 0 if busy else 1))
            d += timedelta(days=1)
        return out

    async def get_bookings(self, prop, since=None):
        return self.bookings

    async def set_rate_range(self, *a, **k):
        self.writes += 1
        return WriteResult(True, True)

    async def aclose(self):
        return None


def _body(bid="900", ci=CI, co=CO, prop=337229, status="confirmed") -> bytes:
    return json.dumps(
        {
            "timeStamp": "2026-10-08T20:00:00Z",
            "booking": {
                "id": int(bid), "propertyId": prop, "roomId": 697411, "status": status,
                "arrival": ci.isoformat() if ci else None,
                "departure": co.isoformat() if co else None,
                "firstName": GUEST, "lastName": "X", "stripeToken": TOKEN,
            },
        }
    ).encode()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    svc._cache.clear()
    monkeypatch.setattr(settings, "beds24_prop_id", "337229")
    yield
    svc._cache.clear()


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


def _use(monkeypatch, cm):
    monkeypatch.setattr(hook_routes, "get_adapter", lambda *_a, **_k: cm)


async def _post(client, body, key=KEY):
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers[webhook_service.HEADER_NAME] = key
    return await client.post("/hooks/beds24", content=body, headers=headers)


async def _bookings(session):
    return list((await session.execute(select(Booking).order_by(Booking.id))).scalars())


async def _events(session):
    return list((await session.execute(select(WebhookEvent).order_by(WebhookEvent.id))).scalars())


# --- US2: autenticación ------------------------------------------------------------


async def test_sin_clave_configurada_503_sin_efectos(client, session, monkeypatch):
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO, channel="booking")])
    _use(monkeypatch, cm)
    r = await _post(client, _body())
    assert r.status_code == 503
    assert await _bookings(session) == [] and cm.rate_ranges == []


async def test_clave_ausente_o_incorrecta_401_rechazado(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO)])
    _use(monkeypatch, cm)
    assert (await _post(client, _body(), key=None)).status_code == 401
    assert (await _post(client, _body(), key="otra")).status_code == 401
    assert await _bookings(session) == [] and cm.rate_ranges == []
    # Feature 026: una clave que no es de ninguna cuenta no tiene cuenta donde registrarse.
    assert await _events(session) == []


async def test_rotacion_de_clave(client, session, monkeypatch):
    _use(monkeypatch, FakeCM([RemoteBooking("900", "697411", CI, CO)]))
    line, hint = await webhook_service.generate_key(session)
    first = line.split(": ", 1)[1]
    line2, _ = await webhook_service.generate_key(session)
    second = line2.split(": ", 1)[1]
    assert (await _post(client, _body(), key=first)).status_code == 401
    assert (await _post(client, _body(), key=second)).status_code == 200


# --- US1: reservas solas -------------------------------------------------------------


async def test_reserva_nueva_aparece_y_ocupa_calendario_sin_escribir(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO, channel="booking", guest_name=GUEST)])
    _use(monkeypatch, cm)
    r = await _post(client, _body())
    assert r.status_code == 200 and r.json() == {"result": "accepted"}
    [b] = await _bookings(session)
    assert (b.external_ref, b.check_in, b.check_out, b.status) == ("900", CI, CO, BookingStatus.confirmed)
    cal = {
        c.date: c.units_available
        for c in (await session.execute(select(CalendarDay))).scalars()
    }
    assert cal[CI] == 0 and cal[CO] == 1  # el día de salida no ocupa
    assert cm.writes == 0  # nunca publica al canal
    [ev] = await _events(session)
    assert ev.result is WebhookResult.accepted and ev.sync_run_id is not None


async def test_cancelacion_libera_y_respeta_bloqueo_manual(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO)])
    _use(monkeypatch, cm)
    await _post(client, _body())
    # el host bloquea a mano una noche fuera de la reserva
    blocked_day = CO + timedelta(days=1)
    session.add(CalendarDay(unit_type_id=1, date=blocked_day, units_available=0, is_blocked=True))
    await session.commit()

    cm.bookings = [RemoteBooking("900", "697411", CI, CO, status="cancelled")]
    r = await _post(client, _body(status="cancelled", co=blocked_day + timedelta(days=1)))
    assert r.json()["result"] == "accepted"
    [b] = await _bookings(session)
    assert b.status is BookingStatus.cancelled
    days = {c.date: c for c in (await session.execute(select(CalendarDay))).scalars()}
    assert days[CI].units_available == 1
    assert days[blocked_day].is_blocked is True  # bloqueo manual intacto


async def test_cambio_de_fechas_resincroniza_tambien_la_estancia_previa(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO)])
    _use(monkeypatch, cm)
    await _post(client, _body())
    new_ci, new_co = CI + timedelta(days=20), CO + timedelta(days=20)
    cm.bookings = [RemoteBooking("900", "697411", new_ci, new_co)]
    await _post(client, _body(ci=new_ci, co=new_co))
    assert cm.rate_ranges[-1] == (CI, new_co)  # incluye las noches viejas para liberarlas
    [b] = await _bookings(session)
    assert (b.check_in, b.check_out) == (new_ci, new_co)


async def test_otra_propiedad_ignorada(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO)])
    _use(monkeypatch, cm)
    r = await _post(client, _body(prop=111))
    assert r.json() == {"result": "ignored"} and cm.rate_ranges == []


# --- US3: robustez ---------------------------------------------------------------------


async def test_duplicado_y_desorden_convergen(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    # Beds24 ya tiene la reserva CANCELADA; llega primero un aviso viejo de "nueva".
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO, status="cancelled")])
    _use(monkeypatch, cm)
    await _post(client, _body(status="confirmed"))
    await _post(client, _body(status="confirmed"))
    await _post(client, _body(status="cancelled"))
    bs = await _bookings(session)
    assert len(bs) == 1 and bs[0].status is BookingStatus.cancelled


async def test_aviso_incompleto_usa_ventana_corta(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    cm = FakeCM()
    _use(monkeypatch, cm)
    r = await _post(client, b"esto no es json")
    assert r.json()["result"] == "accepted"
    assert cm.rate_ranges == [(TODAY, TODAY + timedelta(days=webhook_service.DEFAULT_WINDOW_DAYS))]


async def test_beds24_caido_failed_200_sin_cambios(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    _use(monkeypatch, FakeCM([RemoteBooking("900", "697411", CI, CO)], fail=True))
    r = await _post(client, _body())
    assert r.status_code == 200 and r.json() == {"result": "failed"}
    assert await _bookings(session) == []
    [ev] = await _events(session)
    assert ev.result is WebhookResult.failed and ev.detail == "Beds24 no respondió (ChannelError)"


async def test_reserva_creada_por_otra_via_no_se_duplica(client, session, monkeypatch):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    session.add(Booking(unit_type_id=1, channel_kind="booking", check_in=CI, check_out=CO, external_ref="900"))
    await session.commit()
    _use(monkeypatch, FakeCM([RemoteBooking("900", "697411", CI, CO)]))
    await _post(client, _body())
    assert len(await _bookings(session)) == 1
    assert (await session.execute(select(func.count()).select_from(Booking))).scalar() == 1


async def test_purga_eventos_viejos(session):
    old = WebhookEvent(result=WebhookResult.accepted, received_at=datetime.now(timezone.utc) - timedelta(days=31))
    session.add(old)
    await session.flush()
    await webhook_service.record_rejected(session)
    evs = await _events(session)
    assert [e.result for e in evs] == [WebhookResult.rejected]


async def test_privacidad_cuerpo_no_persistido_ni_logueado(client, session, monkeypatch, caplog):
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY
    _use(monkeypatch, FakeCM([RemoteBooking("900", "697411", CI, CO)]))
    caplog.set_level(logging.DEBUG)
    await _post(client, _body())
    await _post(client, _body(), key="incorrecta")
    rows = " ".join(f"{e.booking_ref}|{e.detail}" for e in await _events(session))
    for secret in (GUEST, TOKEN, KEY):
        assert secret not in rows
        assert secret not in caplog.text


# --- US4: estado y clave -----------------------------------------------------------------


async def test_status_estados_y_clave_mostrada_una_vez(client, session, monkeypatch):
    st = (await client.get("/hooks/beds24/status")).json()
    assert st["status"] == "unconfigured" and st["header_name"] == "X-StayLever-Key"

    gen = (await client.post("/hooks/beds24/key")).json()
    assert gen["header_line"].startswith("X-StayLever-Key: ")
    value = gen["header_line"].split(": ", 1)[1]
    listing = (await client.get("/settings/secrets")).text
    assert value not in listing  # después solo la pista
    assert (await client.get("/hooks/beds24/status")).json()["status"] == "never"

    _use(monkeypatch, FakeCM([RemoteBooking("900", "697411", CI, CO)]))
    assert (await _post(client, _body(), key=value)).status_code == 200
    st = (await client.get("/hooks/beds24/status")).json()
    assert st["status"] == "active" and st["counts_7d"]["accepted"] == 1
    test = (await client.post("/settings/secrets/beds24_webhook_key/test")).json()
    assert test["ok"] is True and "último aviso" in test["detail"]

    idle = await webhook_service.status(session, now=datetime.now(timezone.utc) + timedelta(days=8))
    assert idle["status"] == "idle"


async def test_choque_por_alta_simultanea_reintenta_una_vez(session, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    from app.services import sync_service

    real = sync_service.import_remote
    calls = {"n": 0}

    async def flaky(s, adapter, df, dt, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise IntegrityError("insert booking", {}, Exception("uq_booking_external_ref"))
        return await real(s, adapter, df, dt, **kw)

    monkeypatch.setattr(sync_service, "import_remote", flaky)
    hint = webhook_service.parse_hint(_body())
    ev = await webhook_service.handle(session, FakeCM([RemoteBooking("900", "697411", CI, CO)]), hint)
    assert calls["n"] == 2 and ev.result is WebhookResult.accepted
    assert len(await _bookings(session)) == 1
