"""Feature 028: privacidad de huéspedes, aceptación de términos, exportar y borrar la cuenta."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import date, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core import legal
from app.db.base import Base
from app.db.session import get_session
from app.db.tenancy import mark_platform, set_tenant
from app.email.fake import FakeEmailSender
from app.main import app
from app.models.account import Account, AccountStatus
from app.models.auth import AppUser, Membership, TermsAcceptance
from app.models.booking import Booking
from app.models.enums import ChannelKind
from app.models.property import Property, UnitType
from app.models.secret import SecretEntry
from app.services import admin_service, auth_service, privacy_service

pytestmark = pytest.mark.anyio

PWD = "una-clave-larga-1"
TODAY = date(2026, 10, 14)


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
    monkeypatch.setattr(privacy_service, "platform_session", fake_platform)
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


async def _host_b(client, mail, email="ana@example.com") -> tuple[str, int]:
    """Anfitrión invitado (cuenta nueva), verificado y con sesión."""
    admin = await _admin(client)
    code = (await client.post("/admin/invites", headers=_auth(admin), json={})).json()["code"]
    r = await client.post("/auth/register", json={"name": "Ana", "email": email,
                                                  "password": PWD, "invite_code": code,
                                                  "accept_terms": True})
    assert r.status_code == 202, r.text
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    token = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    me = (await client.get("/auth/me", headers=_auth(token))).json()
    return token, me["account"]["id"]


async def _seed(maker, account_id: int, guest: str, check_out: date) -> int:
    async with maker() as s:
        set_tenant(s, account_id)
        prop = Property(name=f"Casa {account_id}", external_ref=f"p{account_id}")
        s.add(prop)
        await s.flush()
        unit = UnitType(property_id=prop.id, name="Apto", external_ref=f"u{account_id}")
        s.add(unit)
        await s.flush()
        s.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking,
                      check_in=check_out - timedelta(days=3), check_out=check_out,
                      external_ref=f"b{account_id}-{check_out}", guest_name=guest))
        await s.commit()
        return unit.id


# --------- aceptación ---------


async def test_registro_y_reclamacion_exigen_aceptar(client, mail):
    r = await client.post("/auth/claim", json={"name": "Host", "email": "host@example.com",
                                               "password": PWD})
    assert r.status_code == 400 and r.json()["code"] == "terms_required"
    admin = await _admin(client)
    code = (await client.post("/admin/invites", headers=_auth(admin), json={})).json()["code"]
    r = await client.post("/auth/register", json={"name": "Ana", "email": "ana@example.com",
                                                  "password": PWD, "invite_code": code})
    assert r.status_code == 400 and r.json()["code"] == "terms_required"
    # el código no se consumió
    assert (await client.get("/admin/invites", headers=_auth(admin))).json()[0]["status"] == "active"


async def test_puerta_en_el_servidor_y_version_nueva(client, mail, session, monkeypatch):
    token, _ = await _host_b(client, mail)
    me = (await client.get("/auth/me", headers=_auth(token))).json()
    assert me["user"]["terms_required"] is False and me["legal_version"] == legal.LEGAL_VERSION
    assert (await client.get("/units", headers=_auth(token))).status_code == 200
    # se publica una versión nueva → la app deja de responder hasta aceptar
    monkeypatch.setattr(legal, "LEGAL_VERSION", "2099-01-01")
    monkeypatch.setattr(auth_service, "LEGAL_VERSION", "2099-01-01")
    r = await client.get("/units", headers=_auth(token))
    assert r.status_code == 403 and r.json()["code"] == "terms_required"
    me = (await client.get("/auth/me", headers=_auth(token))).json()
    assert me["user"]["terms_required"] is True
    bad = await client.post("/auth/terms/accept", headers=_auth(token), json={"version": "1"})
    assert bad.status_code == 409
    ok = await client.post("/auth/terms/accept", headers=_auth(token),
                           json={"version": "2099-01-01"})
    assert ok.status_code == 200 and ok.json()["user"]["terms_required"] is False
    assert (await client.get("/units", headers=_auth(token))).status_code == 200
    async with session.info["maker"]() as s:
        n = (await s.execute(select(func.count()).select_from(TermsAcceptance))).scalar_one()
        assert n == 3  # host + Ana (versión anterior) + Ana (nueva): se conserva el historial


# --------- nombre del huésped ---------


def test_no_se_guarda_el_nombre_de_estancias_viejas():
    assert privacy_service.keep_guest_name(TODAY - timedelta(days=364), TODAY)
    assert not privacy_service.keep_guest_name(TODAY - timedelta(days=366), TODAY)
    assert privacy_service.keep_guest_name(None, TODAY)


async def test_limpieza_borra_nombres_de_mas_de_un_anio(session):
    maker = session.info["maker"]
    await _seed(maker, 1, "Huésped viejo", TODAY - timedelta(days=400))
    async with maker() as s:
        set_tenant(s, 1)
        unit = (await s.execute(select(UnitType))).scalars().first()
        s.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.airbnb,
                      check_in=TODAY - timedelta(days=340), check_out=TODAY - timedelta(days=335),
                      external_ref="reciente", guest_name="Huésped reciente"))
        await s.commit()
    async with maker() as s:
        set_tenant(s, 1)
        assert await privacy_service.purge_guest_names(s, 1, TODAY) == 1
    async with maker() as s:
        set_tenant(s, 1)
        rows = {b.external_ref: b for b in (await s.execute(select(Booking))).scalars()}
    assert len(rows) == 2  # la reserva vieja se conserva
    old = next(b for k, b in rows.items() if k != "reciente")
    assert old.guest_name is None and old.check_out == TODAY - timedelta(days=400)
    assert rows["reciente"].guest_name == "Huésped reciente"


# --------- exportación ---------


async def test_exportacion_solo_de_la_cuenta_y_sin_secretos(client, mail, session):
    maker = session.info["maker"]
    token, acc_b = await _host_b(client, mail)
    await _seed(maker, 1, "Cliente del host", TODAY)
    await _seed(maker, acc_b, "Cliente de Ana", TODAY)
    async with maker() as s:
        mark_platform(s)
        s.add(SecretEntry(account_id=acc_b, name="beds24_refresh_token",
                          value_encrypted="cifrado", hint="…abcd"))
        await s.commit()
    r = await client.get("/account/export", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["account"]["id"] == acc_b and data["user"]["email"] == "ana@example.com"
    names = [b["guest_name"] for b in data["tables"]["booking"]]
    assert names == ["Cliente de Ana"]
    assert "secret_entry" not in data["tables"] and "cifrado" not in r.text
    assert "password_hash" not in r.text and "Cliente del host" not in r.text
    assert data["terms_acceptances"][0]["version"] == legal.LEGAL_VERSION


# --------- borrado ---------


async def test_borrar_cuenta_elimina_todo_y_no_toca_otras(client, mail, session):
    maker = session.info["maker"]
    token, acc_b = await _host_b(client, mail)
    await _seed(maker, 1, "Cliente del host", TODAY)
    await _seed(maker, acc_b, "Cliente de Ana", TODAY)
    bad = await client.post("/account/delete", headers=_auth(token),
                            json={"account_name": "Otra", "password": PWD})
    assert bad.json()["code"] == "name_mismatch"
    bad = await client.post("/account/delete", headers=_auth(token),
                            json={"account_name": "Ana", "password": "mala-clave-123"})
    assert bad.json()["code"] == "invalid_credentials"
    r = await client.post("/account/delete", headers=_auth(token),
                          json={"account_name": "Ana", "password": PWD})
    assert r.status_code == 200, r.text
    assert "eliminada" in mail.sent[-1].subject.lower() or "elimin" in mail.sent[-1].text.lower()
    # la sesión deja de valer
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 401
    async with maker() as s:
        mark_platform(s)
        for table in Base.metadata.sorted_tables:
            if table.name != "account" and "account_id" in table.c:
                n = (await s.execute(select(func.count()).select_from(table)
                                     .where(table.c.account_id == acc_b))).scalar_one()
                assert n == 0, f"quedaron filas en {table.name}"
        assert (await s.execute(select(AppUser).where(AppUser.email == "ana@example.com"))
                ).scalar_one_or_none() is None
        acc = await s.get(Account, acc_b)
        assert acc.status == AccountStatus.deleted and acc.name == ""
        # la cuenta 1 sigue intacta
        host_b = (await s.execute(select(Booking).where(Booking.account_id == 1))).scalars().all()
        assert [b.guest_name for b in host_b] == ["Cliente del host"]
    admin = (await client.post("/auth/login", json={"email": "host@example.com",
                                                    "password": PWD})).json()["token"]
    accounts = (await client.get("/admin/accounts", headers=_auth(admin))).json()
    assert next(a for a in accounts if a["id"] == acc_b)["status"] == "deleted"
    invites = (await client.get("/admin/invites", headers=_auth(admin))).json()
    assert invites[0]["status"] == "used"
    r = await client.post(f"/admin/accounts/{acc_b}/enable", headers=_auth(admin))
    assert r.status_code == 409


async def test_cuenta_principal_protegida(client, mail):
    admin = await _admin(client)
    r = await client.post("/account/delete", headers=_auth(admin),
                          json={"account_name": "Mi cuenta", "password": PWD})
    assert r.status_code == 409 and r.json()["code"] == "protected"


async def test_borrar_con_codigo_si_no_tiene_contrasena(client, mail, session):
    maker = session.info["maker"]
    async with maker() as s:
        mark_platform(s)
        acc = Account(name="Solo Google")
        s.add(acc)
        await s.flush()
        user = AppUser(email="g@example.com", name="G", password_hash=None, google_sub="g-1")
        s.add(user)
        await s.flush()
        s.add(Membership(user_id=user.id, account_id=acc.id, role="owner"))
        await auth_service.accept_terms(s, user.id)
        token, _ = await auth_service.create_session(s, user, "web")
        await s.commit()
        acc_id = acc.id
    r = await client.post("/account/delete-code", headers=_auth(token))
    assert r.json()["sent"] is True
    code = re.search(r"\b(\d{6})\b", mail.sent[-1].text).group(1)
    wrong = "000000" if code != "000000" else "111111"
    bad = await client.post("/account/delete", headers=_auth(token),
                            json={"account_name": "Solo Google", "code": wrong})
    assert bad.json()["code"] == "invalid_credentials"
    ok = await client.post("/account/delete", headers=_auth(token),
                           json={"account_name": "Solo Google", "code": code})
    assert ok.status_code == 200
    async with maker() as s:
        mark_platform(s)
        assert (await s.get(Account, acc_id)).status == AccountStatus.deleted


async def test_codigo_de_borrado_vence_y_se_agota(client, mail, session):
    maker = session.info["maker"]
    async with maker() as s:
        mark_platform(s)
        acc = Account(name="G2")
        s.add(acc)
        await s.flush()
        user = AppUser(email="g2@example.com", name="G2", password_hash=None)
        s.add(user)
        await s.flush()
        s.add(Membership(user_id=user.id, account_id=acc.id, role="owner"))
        await auth_service.accept_terms(s, user.id)
        token, _ = await auth_service.create_session(s, user, "web")
        await s.commit()
    await client.post("/account/delete-code", headers=_auth(token))
    code = re.search(r"\b(\d{6})\b", mail.sent[-1].text).group(1)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(auth_service.DELETE_CODE_ATTEMPTS):
        await client.post("/account/delete", headers=_auth(token),
                          json={"account_name": "G2", "code": wrong})
    # tras 5 intentos el código correcto ya no sirve
    r = await client.post("/account/delete", headers=_auth(token),
                          json={"account_name": "G2", "code": code})
    assert r.json()["code"] == "invalid_credentials"
