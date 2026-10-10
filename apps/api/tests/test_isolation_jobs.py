"""Feature 026 (principio VI): avisos de Beds24, teléfonos, secretos e importación por cuenta."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

import app.api.routes.hooks as hook_routes
from app.db.cross_account import PropertyOwnedElsewhere
from app.db.session import get_session
from app.main import app
from app.models.booking import Booking
from app.models.enums import WebhookResult
from app.models.push import PushDevice
from app.models.webhook import WebhookEvent
from app.services import push_service, sync_service, webhook_service
from app.services import secret_service as svc
from tests.test_webhooks import CI, CO, FakeCM, RemoteBooking, _body

pytestmark = pytest.mark.anyio

KEY_A = "clave-cuenta-a-123456"
KEY_B = "clave-cuenta-b-654321"
TODAY = date.today()


@pytest.fixture(autouse=True)
def _keys():
    svc._cache.clear()
    svc._cache[(1, webhook_service.KEY_SECRET)] = KEY_A
    svc._cache[(2, webhook_service.KEY_SECRET)] = KEY_B
    yield
    svc._cache.clear()


@pytest_asyncio.fixture
async def hook_client(session, other_session, monkeypatch):
    """Como en producción: la ruta recibe una sesión SIN cuenta y la clave la fija."""
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


async def _post(client, key, bid="900"):
    return await client.post(
        "/hooks/beds24",
        content=_body(bid),
        headers={"Content-Type": "application/json", webhook_service.HEADER_NAME: key},
    )


async def _refs(s):
    return [b.external_ref for b in (await s.execute(select(Booking))).scalars()]


async def test_la_clave_identifica_la_cuenta(hook_client, session, other_session, monkeypatch):
    cm = FakeCM([RemoteBooking("900", "697411", CI, CO, channel="booking")])
    monkeypatch.setattr(hook_routes, "get_adapter", lambda *_a, **_k: cm)

    assert (await _post(hook_client, KEY_A)).json() == {"result": "accepted"}
    assert await _refs(session) == ["900"]
    assert await _refs(other_session) == []

    # B con la MISMA propiedad de Beds24 (ya es de A): no se importa nada en B.
    r = await _post(hook_client, KEY_B)
    assert r.status_code == 200 and r.json()["result"] == "failed"
    assert await _refs(other_session) == []
    evs_b = list((await other_session.execute(select(WebhookEvent))).scalars())
    assert [e.result for e in evs_b] == [WebhookResult.failed]
    evs_a = list((await session.execute(select(WebhookEvent))).scalars())
    assert [e.result for e in evs_a] == [WebhookResult.accepted]

    assert (await _post(hook_client, "clave-de-nadie")).status_code == 401


async def test_importar_propiedad_de_otra_cuenta(session, other_session):
    cm = FakeCM([])
    await sync_service.import_remote(session, cm, TODAY, TODAY + timedelta(days=5))
    await session.commit()
    with pytest.raises(PropertyOwnedElsewhere):
        await sync_service.import_remote(other_session, cm, TODAY, TODAY + timedelta(days=5))


async def test_telefono_pasa_a_la_cuenta_con_sesion(session, other_session):
    await push_service.register_device(session, token="tok-compartido-1")
    await session.commit()
    await push_service.register_device(other_session, token="tok-compartido-1")
    await other_session.commit()
    a = list((await session.execute(select(PushDevice))).scalars())
    b = list((await other_session.execute(select(PushDevice))).scalars())
    assert a == [] and [d.token for d in b] == ["tok-compartido-1"]


async def test_secretos_de_cuenta_no_se_cruzan(session, other_session):
    await svc.set_secret(session, "beds24_refresh_token", "token-de-la-cuenta-A")
    await session.commit()
    assert svc.get_secret("beds24_refresh_token", 1) == "token-de-la-cuenta-A"
    assert svc.get_secret("beds24_refresh_token", 2) is None
    st_b = {s["name"]: s for s in await svc.status(other_session, include_platform=False)}
    assert st_b["beds24_refresh_token"]["configured"] is False
    assert "openai_api_key" not in st_b  # los de plataforma solo los ve el administrador
    with pytest.raises(Exception):
        svc.get_secret("beds24_refresh_token")  # nunca "por defecto"
