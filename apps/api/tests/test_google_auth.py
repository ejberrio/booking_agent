"""Feature 026, entrega 4: Entrar con Google (web y app) con un Google falso."""

from __future__ import annotations

import base64
import json
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db.session import get_session
from app.db.tenancy import mark_platform
from app.email.fake import FakeEmailSender
from app.main import app
from app.models.auth import AppUser, AuthToken
from app.models.mixins import _now
from app.services import admin_service, auth_service
from app.services import google_auth_service as gs

pytestmark = pytest.mark.anyio

CID = "cliente.apps.googleusercontent.com"
PWD = "una-clave-larga-1"


def _id_token(**claims) -> str:
    base = {"iss": "https://accounts.google.com", "aud": CID, "exp": time.time() + 600}
    body = base64.urlsafe_b64encode(json.dumps({**base, **claims}).encode()).rstrip(b"=")
    return f"e30.{body.decode()}.firma"


class FakeGoogle:
    """Endpoint de tokens: comprueba PKCE y devuelve el perfil registrado para cada código."""

    def __init__(self):
        self.profiles: dict[str, dict] = {}
        self.challenges: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        code = form["code"][0]
        if gs.s256(form["code_verifier"][0]) not in self.challenges:
            return httpx.Response(400, json={"error": "invalid_grant"})
        if code not in self.profiles or form["client_secret"][0] != "secreto":
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(200, json={"id_token": _id_token(**self.profiles[code])})


@pytest.fixture
def google(monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(gs, "credentials", lambda: (CID, "secreto"))
    orig = gs._exchange
    transport = httpx.MockTransport(fake.handler)
    monkeypatch.setattr(gs, "_exchange", lambda c, v, cr, _t: orig(c, v, cr, transport))
    return fake


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


async def _start(http, g, **body) -> str:
    r = await http.post("/auth/google/start", json=body)
    assert r.status_code == 200, r.text
    q = parse_qs(urlparse(r.json()["url"]).query)
    assert q["client_id"] == [CID] and q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"][0].endswith("/api/auth/google/callback")
    g.challenges.append(q["code_challenge"][0])
    return q["state"][0]


async def _google_login(http, g, profile, code="c1", **start):
    state = await _start(http, g, **start)
    g.profiles[code] = profile
    return await http.post("/auth/google/callback", json={"code": code, "state": state})


async def _admin(client) -> str:
    r = await client.post("/auth/claim", json={"name": "Host", "email": "host@example.com",
                                               "password": PWD, "accept_terms": True})
    return r.json()["token"]


async def test_sin_credenciales_google_no_esta_disponible(client):
    assert (await client.get("/auth/providers")).json() == {"google": False}
    r = await client.post("/auth/google/start", json={})
    assert r.status_code == 503 and r.json()["code"] == "google_unavailable"


async def test_vincula_por_correo_verificado_y_luego_por_sub(client, google):
    admin = await _admin(client)
    assert (await client.get("/auth/providers")).json() == {"google": True}
    r = await _google_login(client, google, {"sub": "g-1", "email": "Host@Example.com",
                                             "email_verified": True, "name": "Host G"})
    assert r.status_code == 200 and r.json()["client"] == "web"
    me = (await client.get("/auth/me", headers=_auth(r.json()["token"]))).json()
    assert me["account"]["id"] == 1 and me["user"]["is_platform_admin"] is True
    # ya vinculado: entra por `sub` aunque cambie el correo en Google
    r = await _google_login(client, google, {"sub": "g-1", "email": "otro@gmail.com",
                                             "email_verified": True}, code="c2")
    assert r.status_code == 200
    # la sesión con contraseña sigue valiendo
    assert (await client.get("/auth/me", headers=_auth(admin))).status_code == 200


async def test_correo_no_verificado_no_vincula(client, google):
    await _admin(client)
    r = await _google_login(client, google, {"sub": "atacante", "email": "host@example.com",
                                             "email_verified": False})
    assert r.status_code == 403 and r.json()["code"] == "google_unverified"


async def test_registro_con_google_exige_invitacion(client, google, mail):
    admin = await _admin(client)
    r = await _google_login(client, google, {"sub": "g-ana", "email": "ana@gmail.com",
                                             "email_verified": True, "name": "Ana"},
                            mode="register")
    assert r.status_code == 400 and r.json()["code"] == "invite_required"
    code = (await client.post("/admin/invites", headers=_auth(admin), json={})).json()["code"]
    r = await _google_login(client, google, {"sub": "g-ana", "email": "ana@gmail.com",
                                             "email_verified": True, "name": "Ana"},
                            code="c2", mode="register", invite_code=code)
    assert r.status_code == 200
    me = (await client.get("/auth/me", headers=_auth(r.json()["token"]))).json()
    assert me["account"]["id"] != 1 and me["user"]["email_verified"] is True
    assert me["user"]["has_password"] is False and me["account"]["name"] == "Ana"
    invites = (await client.get("/admin/invites", headers=_auth(admin))).json()
    assert invites[0]["status"] == "used"


async def test_estado_invalido_vencido_o_reusado(client, google, session):
    await _admin(client)
    profile = {"sub": "g-1", "email": "host@example.com", "email_verified": True}
    r = await client.post("/auth/google/callback", json={"code": "x", "state": "inventado"})
    assert r.status_code == 400 and r.json()["code"] == "google_state"
    state = await _start(client, google)
    google.profiles["c1"] = profile
    assert (await client.post("/auth/google/callback",
                              json={"code": "c1", "state": state})).status_code == 200
    again = await client.post("/auth/google/callback", json={"code": "c1", "state": state})
    assert again.json()["code"] == "google_state"
    state = await _start(client, google)
    async with session.info["maker"]() as s:
        for row in (await s.execute(select(AuthToken).where(
                AuthToken.purpose == "oauth_state", AuthToken.used_at.is_(None)))).scalars():
            row.expires_at = _now() - timedelta(seconds=1)
        await s.commit()
    r = await client.post("/auth/google/callback", json={"code": "c1", "state": state})
    assert r.json()["code"] == "google_state"


async def test_pkce_codigo_robado_sin_verificador_no_sirve(client, google):
    await _admin(client)
    state = await _start(client, google)
    google.challenges.clear()  # Google rechaza si el verificador no coincide con el challenge
    google.profiles["c1"] = {"sub": "g-1", "email": "host@example.com", "email_verified": True}
    r = await client.post("/auth/google/callback", json={"code": "c1", "state": state})
    assert r.status_code == 400 and r.json()["code"] == "google_failed"


async def test_id_token_de_otro_cliente_se_rechaza(client, google):
    await _admin(client)
    r = await _google_login(client, google, {"sub": "g-1", "email": "host@example.com",
                                             "email_verified": True, "aud": "otro-cliente"})
    assert r.status_code == 400 and r.json()["code"] == "google_failed"


async def test_traspaso_a_la_app(client, google):
    await _admin(client)
    verifier = "v" * 50
    challenge = gs.s256(verifier)
    # la app debe mandar un challenge válido
    bad = await client.post("/auth/google/start", json={"client": "app"})
    assert bad.status_code == 400
    r = await _google_login(client, google, {"sub": "g-1", "email": "host@example.com",
                                             "email_verified": True},
                            client="app", challenge=challenge)
    assert r.status_code == 200 and r.json()["client"] == "app" and "token" not in r.json()
    handoff = r.json()["handoff_code"]
    # verificador equivocado: falla y gasta el código
    wrong = await client.post("/auth/handoff", json={"code": handoff, "verifier": "x" * 50})
    assert wrong.status_code == 400
    again = await client.post("/auth/handoff", json={"code": handoff, "verifier": verifier})
    assert again.status_code == 400
    # flujo completo correcto
    r = await _google_login(client, google, {"sub": "g-1", "email": "host@example.com",
                                             "email_verified": True},
                            code="c2", client="app", challenge=challenge)
    ok = await client.post("/auth/handoff",
                           json={"code": r.json()["handoff_code"], "verifier": verifier})
    assert ok.status_code == 200
    me = await client.get("/auth/me", headers=_auth(ok.json()["token"]))
    assert me.status_code == 200
    reused = await client.post("/auth/handoff",
                               json={"code": r.json()["handoff_code"], "verifier": verifier})
    assert reused.status_code == 400


async def test_cuenta_desactivada_no_entra_con_google(client, google, mail):
    admin = await _admin(client)
    code = (await client.post("/admin/invites", headers=_auth(admin), json={})).json()["code"]
    profile = {"sub": "g-ana", "email": "ana@gmail.com", "email_verified": True, "name": "Ana"}
    r = await _google_login(client, google, profile, mode="register", invite_code=code)
    acc = (await client.get("/auth/me", headers=_auth(r.json()["token"]))).json()["account"]["id"]
    await client.post(f"/admin/accounts/{acc}/disable", headers=_auth(admin))
    r = await _google_login(client, google, profile, code="c2")
    assert r.status_code == 403 and r.json()["code"] == "disabled"


async def test_usuario_creado_con_google_no_tiene_contrasena(client, google, session):
    admin = await _admin(client)
    code = (await client.post("/admin/invites", headers=_auth(admin), json={})).json()["code"]
    await _google_login(client, google, {"sub": "g-b", "email": "b@gmail.com",
                                         "email_verified": True}, mode="register",
                        invite_code=code)
    async with session.info["maker"]() as s:
        u = (await s.execute(select(AppUser).where(AppUser.email == "b@gmail.com"))).scalar_one()
        assert u.password_hash is None and u.google_sub == "g-b"
    r = await client.post("/auth/login", json={"email": "b@gmail.com", "password": PWD})
    assert r.status_code == 401
