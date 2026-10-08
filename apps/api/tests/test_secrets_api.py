"""Feature 017: endpoints write-only de secretos (estado, PUT/DELETE, test, audit).

SC-002: el valor centinela no debe aparecer en NINGUNA respuesta.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

import app.api.routes.secrets as secrets_routes
from app.db.session import get_session
from app.main import app
from app.services import secret_service as svc

pytestmark = pytest.mark.anyio

SENTINEL = "SENTINEL-XYZ-1234"


@pytest.fixture(autouse=True)
def _clean_cache():
    svc._cache.clear()
    svc._unreadable.clear()
    yield
    svc._cache.clear()
    svc._unreadable.clear()


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_put_get_delete_sin_fugas(client, session):
    # PUT: estado sin eco del valor
    res = await client.put("/settings/secrets/search_api_key", json={"value": SENTINEL})
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "app" and body["hint"] == "…1234"
    assert SENTINEL not in res.text  # SC-002

    # rotación efectiva sin recargar
    assert svc.get_secret("search_api_key") == SENTINEL

    # GET estado: enmascarado
    listing = await client.get("/settings/secrets")
    assert SENTINEL not in listing.text
    st = {s["name"]: s for s in listing.json()["secrets"]}
    assert st["search_api_key"]["configured"] is True
    assert st["search_api_key"]["source"] == "app"

    # audit: solo pista
    audit = await client.get("/settings/secrets/audit")
    assert SENTINEL not in audit.text
    assert audit.json()["entries"][0]["action"] == "set"

    # DELETE → vuelve a env/None
    dele = await client.delete("/settings/secrets/search_api_key")
    assert dele.status_code == 200
    assert SENTINEL not in dele.text
    assert (await client.delete("/settings/secrets/search_api_key")).status_code == 404


async def test_validaciones_endpoint(client, session):
    assert (
        await client.put("/settings/secrets/search_api_key", json={"value": "   "})
    ).status_code == 422
    assert (
        await client.put("/settings/secrets/no_gestionable", json={"value": "x" * 20})
    ).status_code == 404
    assert (await client.post("/settings/secrets/no_gestionable/test")).status_code == 404


async def test_probar_servicios_con_dobles(client, session, monkeypatch):
    async def fake_ok(_name=None):
        return {"ok": True, "detail": "conexión OK"}

    async def fake_bad(_name=None):
        return {"ok": False, "detail": "credencial rechazada por el proveedor"}

    monkeypatch.setattr(secrets_routes, "_test_llm", fake_ok)
    monkeypatch.setattr(secrets_routes, "_test_search", lambda: fake_bad())
    monkeypatch.setattr(secrets_routes, "_test_beds24", lambda: fake_ok())

    ok = await client.post("/settings/secrets/openai_api_key/test")
    assert ok.json() == {"ok": True, "detail": "conexión OK"}
    bad = await client.post("/settings/secrets/search_api_key/test")
    assert bad.json()["ok"] is False
    assert SENTINEL not in bad.text

    b24 = await client.post("/settings/secrets/beds24_refresh_token/test")
    assert b24.json()["ok"] is True


async def test_probar_sin_credencial(client, session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "openai_api_key", None)
    res = await client.post("/settings/secrets/openai_api_key/test")
    assert res.json() == {"ok": False, "detail": "sin credencial configurada"}


async def test_canje_codigo_invitacion_beds24_sin_fugas(client, monkeypatch):
    import app.channels.beds24_v2 as v2
    from app.channels.errors import AuthError

    async def fake_exchange(code, **_kw):
        if code == "INVITE-OK":
            return SENTINEL
        raise AuthError("código de invitación rechazado por Beds24")

    monkeypatch.setattr(v2, "exchange_invite_code", fake_exchange)

    res = await client.post(
        "/settings/secrets/beds24_refresh_token/invite", json={"code": "INVITE-OK"}
    )
    assert res.status_code == 200
    assert SENTINEL not in res.text and "INVITE-OK" not in res.text
    assert res.json()["source"] == "app"
    assert svc.get_secret("beds24_refresh_token") == SENTINEL  # rotación inmediata

    bad = await client.post(
        "/settings/secrets/beds24_refresh_token/invite", json={"code": "INVITE-BAD"}
    )
    assert bad.status_code == 422 and "INVITE-BAD" not in bad.text
    empty = await client.post("/settings/secrets/beds24_refresh_token/invite", json={"code": " "})
    assert empty.status_code == 422
