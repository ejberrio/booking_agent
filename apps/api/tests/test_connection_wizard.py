"""Feature 044 (#150): conectar Beds24 desde StayLever — selección, conflictos y salud."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.channels.base import RemoteProperty, RemoteRoom
from app.db.cross_account import PropertyOwnedElsewhere
from app.models.enums import ConnectionStatus
from app.models.property import Property, UnitType
from app.services import connection_service as svc
from app.services import sync_service
from tests.test_webhooks import FakeCM

pytestmark = pytest.mark.anyio
TODAY = date.today()


class TwoProps(FakeCM):
    async def get_properties(self):
        return [
            RemoteProperty("111", "Apto Mayorca", "COP",
                           [RemoteRoom("1001", "3BR", 1), RemoteRoom("1002", "Estudio", 1)]),
            RemoteProperty("222", "Casa finca", "COP", [RemoteRoom("2001", "Casa", 1)]),
        ]

    async def get_rates(self, room, df, dt):
        return []


async def _import(session, cm=None):
    return await sync_service.import_remote(session, cm or TwoProps([]), TODAY, TODAY + timedelta(days=3))


async def test_solo_importa_lo_elegido(session):
    await svc.set_selection(session, ["1001"])
    await _import(session)
    assert [u.external_ref for u in (await session.execute(select(UnitType))).scalars()] == ["1001"]
    assert [p.external_ref for p in (await session.execute(select(Property))).scalars()] == ["111"]
    await svc.set_selection(session, None)  # None = todas
    await _import(session)
    refs = sorted(u.external_ref for u in (await session.execute(select(UnitType))).scalars())
    assert refs == ["1001", "1002", "2001"]


async def test_propiedad_de_otra_cuenta_no_tumba_las_demas(session, other_session):
    cm = FakeCM([])  # propiedad 337229
    await sync_service.import_remote(session, cm, TODAY, TODAY + timedelta(days=3))
    await session.commit()

    class Mixed(TwoProps):
        async def get_properties(self):
            return [*(await FakeCM.get_properties(self)), *(await TwoProps.get_properties(self))]

    await sync_service.import_remote(other_session, Mixed([]), TODAY, TODAY + timedelta(days=3))
    mine = sorted(p.external_ref for p in (await other_session.execute(select(Property))).scalars())
    assert mine == ["111", "222"]  # la de la otra cuenta se saltó sin abortar
    with pytest.raises(PropertyOwnedElsewhere):  # si no queda nada importable, el 409 de siempre
        await sync_service.import_remote(other_session, cm, TODAY, TODAY + timedelta(days=3))


class FakePush:
    def __init__(self):
        self.sent = []

    async def send(self, msg):
        from app.push.base import PushResult

        self.sent.append(msg)
        return PushResult("ok")

    async def aclose(self):
        return None


class FakeMail:
    def __init__(self):
        self.sent = []

    async def send(self, msg):
        self.sent.append(msg)


async def test_conexion_caida_avisa_una_vez_recuerda_a_los_3_dias_y_se_limpia(session):
    from app.models.auth import AppUser, Membership
    from app.services import push_service

    user = AppUser(name="Ana", email="ana@example.com", password_hash="x", language="es",
                   email_verified_at=datetime.now(UTC))
    session.add(user)
    await session.flush()
    session.add(Membership(user_id=user.id, account_id=1, role="owner"))
    await push_service.register_device(session, token="tok-1")
    await session.flush()
    push, mail = FakePush(), FakeMail()
    t0 = datetime(2026, 11, 5, 10, tzinfo=UTC)

    assert await svc.record_auth_failure(session, "token revocado", now=t0, push_sender=push,
                                         email_sender=mail)
    assert not await svc.record_auth_failure(session, "otra vez", now=t0 + timedelta(hours=6),
                                             push_sender=push, email_sender=mail)
    assert len(mail.sent) == 1 and "Beds24" in mail.sent[0].subject and len(push.sent) == 1
    assert "/onboarding" in mail.sent[0].text
    conn = await svc.get(session)
    assert conn.status == ConnectionStatus.invalid and conn.invalid_since.replace(tzinfo=UTC) == t0

    assert not await svc.remind_if_due(session, now=t0 + timedelta(days=2), email_sender=mail,
                                       push_sender=push)
    assert await svc.remind_if_due(session, now=t0 + timedelta(days=3, hours=1), email_sender=mail,
                                   push_sender=push)
    assert not await svc.remind_if_due(session, now=t0 + timedelta(days=5), email_sender=mail,
                                       push_sender=push)
    assert len(mail.sent) == 2 and "Recordatorio" in mail.sent[1].subject

    assert await svc.record_ok(session, "Apto")  # se restableció
    conn = await svc.get(session)
    assert conn.status == ConnectionStatus.connected and conn.invalid_since is None
    assert conn.alerted_at is None and conn.reminded_at is None


async def test_seleccion_y_salud_aisladas_por_cuenta(session, other_session):
    await svc.set_selection(session, ["1001"])
    await svc.record_auth_failure(session, "x", push_sender=FakePush(), email_sender=FakeMail())
    await session.commit()
    assert await svc.selected_rooms(other_session) is None
    assert svc.health((await svc.get(other_session)))["status"] == "unconfigured"


# --------- rutas del asistente ---------

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.services import secret_service  # noqa: E402

SENTINEL = "TOKEN-SECRETO-XYZ"


class WizardCM(TwoProps):
    async def test_connection(self):
        from app.channels.base import ConnectionInfo

        return ConnectionInfo(ok=True, properties=await self.get_properties())


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    import app.api.routes.connection as routes
    import app.channels.beds24_v2 as v2
    from app.channels.errors import AuthError

    async def fake_exchange(code, **_kw):
        if code == "INVITE-OK":
            return SENTINEL
        raise AuthError("rechazado")

    monkeypatch.setattr(v2, "exchange_invite_code", fake_exchange)
    monkeypatch.setattr(routes, "get_adapter", lambda s: WizardCM([]))
    monkeypatch.setattr(routes.settings, "channel_mode", "real")
    secret_service._cache.clear()

    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)
    secret_service._cache.clear()


async def test_asistente_canje_lista_y_seleccion_sin_fugas(client):
    bad = await client.post("/connection/beds24/redeem", json={"code": "INVITE-VENCIDO"})
    assert bad.status_code == 422 and "vencido" in bad.json()["detail"]

    ok = await client.post("/connection/beds24/redeem", json={"code": "INVITE-OK"})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert SENTINEL not in ok.text and "INVITE-OK" not in ok.text
    assert [p["id"] for p in body["properties"]] == ["111", "222"]
    assert all(r["selected"] for p in body["properties"] for r in p["rooms"])  # todo marcado

    st = (await client.get("/connection")).json()
    assert st["status"] == "connected" and st["has_token"] and SENTINEL not in str(st)

    assert (await client.put("/connection/beds24/selection", json={"room_ids": []})).status_code == 422
    r = await client.put("/connection/beds24/selection", json={"room_ids": ["1001", "2001"]})
    assert r.status_code == 200
    rooms = (await client.get("/connection/beds24/rooms")).json()
    sel = {rm["id"]: rm["selected"] for p in rooms["properties"] for rm in p["rooms"]}
    assert sel == {"1001": True, "1002": False, "2001": True}
