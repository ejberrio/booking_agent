"""Feature 013 · US1: endpoints /pricing/channel-offsets (T007).

Único suite de endpoints con BD del repo: fixture local con ASGITransport y
override de get_session sobre la MISMA sesión SQLite del test.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

import app.api.routes.pricing as pricing_routes
from app.db.session import get_session
from app.main import app
from app.models.enums import ChannelKind
from app.models.property import Channel, Property, UnitType
from tests.test_channel_pricing_service import FakeCM

pytestmark = pytest.mark.anyio


@pytest.fixture()
def fake_cm(monkeypatch):
    cm = FakeCM()

    async def _noop_close():
        return None

    cm.aclose = _noop_close
    monkeypatch.setattr(pricing_routes, "get_adapter", lambda *_a, **_k: cm)
    return cm


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _seed(session):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    session.add(Channel(property_id=prop.id, kind=ChannelKind.airbnb, is_active=True))
    await session.flush()


async def test_get_offsets_endpoint(client, session, fake_cm):
    await _seed(session)
    res = await client.get("/pricing/channel-offsets")
    assert res.status_code == 200
    by = {o["channel"]: o for o in res.json()["offsets"]}
    assert by["airbnb"]["supported"] is True
    assert by["booking"]["supported"] is False


async def test_preview_endpoint_rejects_out_of_range(client, session, fake_cm):
    await _seed(session)
    res = await client.post(
        "/pricing/channel-offsets/preview", json={"channel": "airbnb", "offset_pct": 500}
    )
    assert res.status_code == 422


async def test_preview_endpoint_honest_for_booking(client, session, fake_cm):
    await _seed(session)
    res = await client.post(
        "/pricing/channel-offsets/preview", json={"channel": "booking", "offset_pct": 5}
    )
    assert res.status_code == 422
    assert "precio base" in res.json()["detail"]


async def test_preview_then_apply_flow(client, session, fake_cm):
    await _seed(session)
    res = await client.post(
        "/pricing/channel-offsets/preview", json={"channel": "airbnb", "offset_pct": 8}
    )
    assert res.status_code == 200
    fp = res.json()["fingerprint"]

    res2 = await client.post(
        "/pricing/channel-offsets/apply",
        json={"channel": "airbnb", "offset_pct": 8, "fingerprint": fp},
    )
    assert res2.status_code == 200
    body = res2.json()
    assert body["applied"] is True and body["verified"] is True


async def test_apply_endpoint_invalid_fingerprint(client, session, fake_cm):
    await _seed(session)
    res = await client.post(
        "/pricing/channel-offsets/apply",
        json={"channel": "airbnb", "offset_pct": 8, "fingerprint": "nope"},
    )
    assert res.status_code == 409
