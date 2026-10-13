"""Feature 026, entrega 2: acceso por usuario (sesiones, contraseñas, correos, reclamación)."""

from __future__ import annotations

import re
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_session
from app.email.fake import FakeEmailSender
from app.main import app
from app.models.account import Account, AccountStatus
from app.models.auth import AppUser, UserSession
from app.models.mixins import _now
from app.services import auth_service

pytestmark = pytest.mark.anyio

PWD = "una-clave-larga-1"
NEW_PWD = "otra-clave-larga-2"


@pytest.fixture
def mail(monkeypatch):
    sender = FakeEmailSender()
    monkeypatch.setattr(auth_service, "get_email_sender", lambda: sender)
    return sender


@pytest_asyncio.fixture
async def client(session):
    """Como en producción: la ruta recibe una sesión SIN cuenta (la pone require_ctx)."""
    maker = session.info["maker"]

    async def _fresh():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _fresh
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


def _link_token(msg) -> str:
    return re.search(r"token=([A-Za-z0-9_\-]+)", msg.text).group(1)


async def _claim(client, email="host@example.com"):
    r = await client.post("/auth/claim", json={"name": "Host", "email": email, "password": PWD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_reclamar_la_cuenta_1_una_sola_vez(client, mail):
    assert (await client.get("/auth/claim-status")).json() == {"claimable": True}
    token = await _claim(client)
    me = (await client.get("/auth/me", headers=_auth(token))).json()
    assert me["user"]["is_platform_admin"] and me["account"]["id"] == 1
    assert me["user"]["email_verified"] is False
    assert len(mail.sent) == 1 and "verify" in mail.sent[0].text  # correo de verificación
    assert (await client.get("/auth/claim-status")).json() == {"claimable": False}
    r = await client.post("/auth/claim", json={"name": "X", "email": "x@example.com",
                                               "password": PWD})
    assert r.status_code == 409


async def test_login_sesion_y_rutas_protegidas(client, mail, monkeypatch):
    await _claim(client)
    r = await client.post("/auth/login", json={"email": "HOST@example.com ", "password": PWD})
    assert r.status_code == 200
    token = r.json()["token"]
    assert (await client.get("/units", headers=_auth(token))).status_code == 200
    # token inventado → 401 (nunca cae a la cuenta 1)
    assert (await client.get("/units", headers=_auth("falso-123"))).status_code == 401
    # modo sesiones: sin token → 401
    monkeypatch.setattr(settings, "auth_mode", "sessions")
    assert (await client.get("/units")).status_code == 401
    assert (await client.get("/units", headers=_auth(token))).status_code == 200


async def test_errores_genericos_y_bloqueo(client, mail):
    await _claim(client)
    bad = await client.post("/auth/login", json={"email": "host@example.com", "password": "mal"})
    nobody = await client.post("/auth/login", json={"email": "nadie@example.com",
                                                    "password": "mal"})
    assert bad.status_code == nobody.status_code == 401
    assert bad.json()["detail"] == nobody.json()["detail"]
    for _ in range(9):
        await client.post("/auth/login", json={"email": "host@example.com", "password": "mal"})
    r = await client.post("/auth/login", json={"email": "host@example.com", "password": PWD})
    assert r.status_code == 429  # bloqueado aunque ahora acierte


async def test_logout_y_logout_all(client, mail):
    t1 = await _claim(client)
    t2 = (await client.post("/auth/login", json={"email": "host@example.com", "password": PWD,
                                                 "kind": "app"})).json()["token"]
    assert (await client.post("/auth/logout", headers=_auth(t1))).status_code == 204
    assert (await client.get("/units", headers=_auth(t1))).status_code == 401
    assert (await client.get("/units", headers=_auth(t2))).status_code == 200
    assert (await client.post("/auth/logout-all", headers=_auth(t2))).status_code == 204
    assert (await client.get("/units", headers=_auth(t2))).status_code == 401


async def test_duracion_web_y_app(session):
    user = AppUser(email="a@example.com", name="A")
    session.add(user)
    await session.flush()
    _, exp_web = await auth_service.create_session(session, user, "web")
    _, exp_app = await auth_service.create_session(session, user, "app")
    assert timedelta(days=6) < exp_web - _now() <= timedelta(days=7)
    assert timedelta(days=89) < exp_app - _now() <= timedelta(days=90)


async def test_sesion_vencida_y_cuenta_desactivada(client, mail, session):
    token = await _claim(client)
    maker = session.info["maker"]
    async with maker() as s:
        row = (await s.execute(select(UserSession))).scalars().first()
        row.expires_at = _now() - timedelta(minutes=1)
        await s.commit()
    assert (await client.get("/units", headers=_auth(token))).status_code == 401
    token = (await client.post("/auth/login", json={"email": "host@example.com",
                                                    "password": PWD})).json()["token"]
    async with maker() as s:
        acc = await s.get(Account, 1)
        acc.status = AccountStatus.disabled
        await s.commit()
    assert (await client.get("/units", headers=_auth(token))).status_code == 401
    r = await client.post("/auth/login", json={"email": "host@example.com", "password": PWD})
    assert r.status_code == 403 and r.json()["code"] == "disabled"


async def test_verificar_correo_enlace_de_un_solo_uso(client, mail):
    await _claim(client)
    tok = _link_token(mail.sent[0])
    r = await client.post("/auth/verify-email", json={"token": tok})
    assert r.status_code == 200 and r.json()["token"]
    assert (await client.post("/auth/verify-email", json={"token": tok})).status_code == 400


async def test_recuperar_contrasena_cierra_las_sesiones(client, mail):
    old = await _claim(client)
    r = await client.post("/auth/forgot-password", json={"email": "host@example.com"})
    assert r.status_code == 202
    assert (await client.post("/auth/forgot-password", json={"email": "nadie@example.com"})
            ).status_code == 202  # misma respuesta: no revela si existe
    reset_mail = mail.sent[-1]
    assert "reset" in reset_mail.text
    tok = _link_token(reset_mail)
    weak = await client.post("/auth/reset-password", json={"token": tok, "password": "corta"})
    assert weak.status_code == 400 and weak.json()["code"] == "weak_password"
    ok = await client.post("/auth/reset-password", json={"token": tok, "password": NEW_PWD})
    assert ok.status_code == 200
    assert (await client.get("/units", headers=_auth(old))).status_code == 401
    assert (await client.post("/auth/login", json={"email": "host@example.com",
                                                   "password": NEW_PWD})).status_code == 200
    assert (await client.post("/auth/reset-password", json={"token": tok, "password": NEW_PWD})
            ).status_code == 400


async def test_cambiar_contrasena_mantiene_la_sesion_actual(client, mail):
    t1 = await _claim(client)
    t2 = (await client.post("/auth/login", json={"email": "host@example.com",
                                                 "password": PWD})).json()["token"]
    r = await client.post("/auth/change-password", headers=_auth(t1),
                          json={"current": PWD, "new": NEW_PWD})
    assert r.status_code == 200
    assert (await client.get("/units", headers=_auth(t1))).status_code == 200
    assert (await client.get("/units", headers=_auth(t2))).status_code == 401


async def test_usuario_normal_sin_verificar_no_entra(session, client, mail):
    from app.auth.passwords import hash_password
    from app.models.auth import Membership

    maker = session.info["maker"]
    async with maker() as s:
        from app.db.tenancy import mark_platform

        mark_platform(s)
        s.add(Account(id=2, name="B"))
        u = AppUser(email="b@example.com", name="B", password_hash=hash_password(PWD))
        s.add(u)
        await s.flush()
        s.add(Membership(user_id=u.id, account_id=2))
        await s.commit()
    r = await client.post("/auth/login", json={"email": "b@example.com", "password": PWD})
    assert r.status_code == 403 and r.json()["code"] == "email_unverified"


async def test_auditoria_guarda_el_usuario(client, mail, session, monkeypatch):
    from datetime import date

    from app.models.audit import PriceChangeLog
    from app.models.property import Property, UnitType

    token = await _claim(client)
    prop = Property(name="P", external_ref="1")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="U", external_ref="2")
    session.add(unit)
    await session.commit()
    sel = {"date_from": str(date.today() + timedelta(days=3)),
           "date_to": str(date.today() + timedelta(days=3))}
    prev = (await client.post("/pricing/range/preview", headers=_auth(token),
                              json={"unit_type_id": unit.id, "selection": sel,
                                    "price": 300000})).json()
    import app.api.routes.pricing as pricing_routes

    class CM:
        async def set_rate_range(self, *a, **k):
            from app.channels.base import WriteResult
            return WriteResult(True, True)

        async def set_calendar_entries(self, *a, **k):
            from app.channels.base import WriteResult
            return WriteResult(True, True)

        async def aclose(self):
            return None

    monkeypatch.setattr(pricing_routes, "get_adapter", lambda *_a, **_k: CM())
    r = await client.post("/pricing/range/apply", headers=_auth(token),
                          json={"unit_type_id": unit.id, "selection": sel, "price": 300000,
                                "fingerprint": prev["fingerprint"]})
    assert r.status_code == 200, r.text
    log = (await session.execute(select(PriceChangeLog))).scalars().first()
    me = (await client.get("/auth/me", headers=_auth(token))).json()
    assert log.user_id == me["user"]["id"]
