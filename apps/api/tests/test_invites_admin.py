"""Feature 026, entrega 3: invitaciones, registro y panel del administrador de plataforma."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db.session import get_session
from app.db.tenancy import mark_platform
from app.email.fake import FakeEmailSender
from app.main import app
from app.models.account import Account
from app.models.auth import InviteCode
from app.models.mixins import _now
from app.services import admin_service, auth_service, invite_service

pytestmark = pytest.mark.anyio

PWD = "una-clave-larga-1"


@pytest.fixture
def mail(monkeypatch):
    sender = FakeEmailSender()
    monkeypatch.setattr(auth_service, "get_email_sender", lambda: sender)
    return sender


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    maker = session.info["maker"]

    async def _fresh():
        async with maker() as s:
            yield s

    @asynccontextmanager
    async def fake_platform():
        async with maker() as s:
            mark_platform(s)
            yield s

    monkeypatch.setattr(admin_service, "platform_session", fake_platform)
    app.dependency_overrides[get_session] = _fresh
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _admin(client) -> str:
    r = await client.post("/auth/claim", json={"name": "Host", "email": "host@example.com",
                                               "password": PWD, "accept_terms": True})
    return r.json()["token"]


async def _invite(client, token, note="Ana"):
    r = await client.post("/admin/invites", headers=_auth(token), json={"note": note})
    assert r.status_code == 200, r.text
    return r.json()


async def _register(client, code, email="ana@example.com"):
    return await client.post("/auth/register", json={"name": "Ana", "email": email,
                                                     "password": PWD, "invite_code": code,
                                                     "accept_terms": True})


def test_formato_y_normalizacion_del_codigo():
    assert invite_service.normalize_code("sl-ab12 cd34") == "SL-AB12-CD34"
    assert invite_service.normalize_code("SL AB1O-CDLI") == "SL-AB10-CD11"  # O→0, L/I→1
    assert invite_service.normalize_code("hola") == ""


async def test_invitar_registrar_verificar_y_entrar(client, mail):
    admin = await _admin(client)
    inv = await _invite(client, admin)
    assert re.fullmatch(r"SL-[0-9A-Z]{4}-[0-9A-Z]{4}", inv["code"])
    listed = (await client.get("/admin/invites", headers=_auth(admin))).json()
    assert listed[0]["status"] == "active" and "code" not in listed[0]  # el código no se repite

    r = await _register(client, inv["code"].lower())
    assert r.status_code == 202
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    # sin verificar no entra
    r = await client.post("/auth/login", json={"email": "ana@example.com", "password": PWD})
    assert r.json()["code"] == "email_unverified"
    token = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    me = (await client.get("/auth/me", headers=_auth(token))).json()
    assert me["account"]["id"] != 1 and me["user"]["is_platform_admin"] is False
    # cuenta nueva vacía, sin errores
    assert (await client.get("/units", headers=_auth(token))).json() == []
    assert (await client.get("/suggestions?pending=true", headers=_auth(token))).json() == []
    assert (await client.get("/status", headers=_auth(token))).status_code == 200
    # el código quedó usado por esa cuenta
    listed = (await client.get("/admin/invites", headers=_auth(admin))).json()
    assert listed[0]["status"] == "used" and listed[0]["used_by_account"]["name"] == "Ana"
    # y no sirve otra vez
    again = await _register(client, inv["code"], email="otra@example.com")
    assert again.status_code == 400 and again.json()["code"] == "invite_invalid"


async def test_registro_cerrado_abierto_y_correo_existente(client, mail):
    admin = await _admin(client)
    r = await _register(client, None)
    assert r.status_code == 400 and r.json()["code"] == "invite_required"
    inv = await _invite(client, admin)
    # correo ya registrado: misma respuesta, aviso por correo y el código NO se consume
    r = await _register(client, inv["code"], email="host@example.com")
    assert r.status_code == 202 and "ya tienes una cuenta" in mail.sent[-1].text.lower()
    listed = (await client.get("/admin/invites", headers=_auth(admin))).json()
    assert listed[0]["status"] == "active"
    # registro abierto: sin código
    await client.patch("/admin/settings", headers=_auth(admin), json={"registration_open": True})
    assert (await client.get("/auth/registration-status")).json() == {"open": True}
    assert (await _register(client, None, email="libre@example.com")).status_code == 202


async def test_codigo_vencido_revocado_y_uso_simultaneo(client, mail, session):
    admin = await _admin(client)
    a = await _invite(client, admin, "vence")
    b = await _invite(client, admin, "revoca")
    c = await _invite(client, admin, "doble")
    async with session.info["maker"]() as s:
        row = (await s.execute(select(InviteCode).where(InviteCode.note == "vence"))).scalar_one()
        row.expires_at = _now() - timedelta(minutes=1)
        await s.commit()
    assert (await _register(client, a["code"])).json()["code"] == "invite_invalid"
    assert (await client.delete(f"/admin/invites/{b['id']}", headers=_auth(admin))).status_code == 200
    assert (await _register(client, b["code"])).json()["code"] == "invite_invalid"
    # Consumo atómico: el UPDATE condicional solo gana una vez (en SQLite de pruebas las
    # sesiones comparten conexión, así que la carrera real se prueba a nivel de servicio).
    async with session.info["maker"]() as s:
        row = (await s.execute(select(InviteCode).where(InviteCode.note == "doble"))).scalar_one()
        assert await invite_service.consume(s, row, 1) is True
        assert await invite_service.consume(s, row, 1) is False
        await s.commit()
    assert (await _register(client, c["code"], email="dos@example.com")).status_code == 400
    # un código usado no se puede revocar
    assert (await client.delete(f"/admin/invites/{c['id']}", headers=_auth(admin))).status_code == 409


async def test_panel_solo_admin_y_cuentas_sin_datos_privados(client, mail):
    admin = await _admin(client)
    inv = await _invite(client, admin)
    await _register(client, inv["code"])
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    user = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    # no admin → 403
    assert (await client.get("/admin/accounts", headers=_auth(user))).status_code == 403
    assert (await client.post("/admin/invites", headers=_auth(user), json={})).status_code == 403
    accounts = (await client.get("/admin/accounts", headers=_auth(admin))).json()
    assert {a["id"] for a in accounts} >= {1}
    assert set(accounts[0]) == {"id", "name", "owner_email", "status", "created_at",
                                "last_seen_at", "connected", "properties"}
    ana = next(a for a in accounts if a["name"] == "Ana")
    assert ana["last_seen_at"] is not None  # entrar cuenta como uso
    # desactivar → sus sesiones dejan de valer; reactivar
    r = await client.post(f"/admin/accounts/{ana['id']}/disable", headers=_auth(admin))
    assert r.json()["status"] == "disabled"
    assert (await client.get("/units", headers=_auth(user))).status_code == 401
    r = await client.post("/auth/login", json={"email": "ana@example.com", "password": PWD})
    assert r.json()["code"] == "disabled"
    await client.post(f"/admin/accounts/{ana['id']}/enable", headers=_auth(admin))
    r = await client.post("/auth/login", json={"email": "ana@example.com", "password": PWD})
    assert r.status_code == 200
    # la cuenta principal no se desactiva
    assert (await client.post("/admin/accounts/1/disable", headers=_auth(admin))).status_code == 409


async def test_registro_sin_correo_configurado(client, monkeypatch):
    monkeypatch.setattr(auth_service, "get_email_sender", lambda: None)
    r = await _register(client, "SL-AAAA-BBBB")
    assert r.status_code == 503


async def test_cuenta_nueva_no_ve_la_cuenta_1(client, mail, session):
    from app.models.property import Property

    session.add(Property(name="Casa del host", external_ref="337229"))
    await session.commit()
    admin = await _admin(client)
    inv = await _invite(client, admin)
    await _register(client, inv["code"])
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    user = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    assert (await client.get("/units", headers=_auth(user))).json() == []
    async with session.info["maker"]() as s:
        mark_platform(s)
        assert len((await s.execute(select(Account))).scalars().all()) == 2


async def test_cambiar_mi_nombre_y_el_de_la_cuenta(client, mail):
    admin = await _admin(client)
    r = await client.patch("/auth/me", headers=_auth(admin), json={"name": "  Ever  "})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Ever"
    r = await client.patch("/account", headers=_auth(admin), json={"name": "Apto Laureles"})
    assert r.json()["name"] == "Apto Laureles"
    me = (await client.get("/auth/me", headers=_auth(admin))).json()
    assert me["user"]["name"] == "Ever" and me["account"]["name"] == "Apto Laureles"
    assert (await client.patch("/auth/me", headers=_auth(admin), json={"name": "   "})).status_code == 400
    assert (await client.patch("/auth/me", json={"name": "X"})).status_code == 401
