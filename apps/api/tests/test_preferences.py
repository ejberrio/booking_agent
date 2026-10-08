"""Feature 021: preferencia de idioma del host (fila única)."""

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import get_session
from app.main import app
from app.models.preference import AppPreference

pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_default_es_y_cambio_persistente(client, session):
    assert (await client.get("/preferences")).json() == {"language": "es"}
    assert (await client.put("/preferences", json={"language": "en"})).json() == {"language": "en"}
    assert (await client.get("/preferences")).json() == {"language": "en"}
    await client.put("/preferences", json={"language": "pt"})
    count = (await session.execute(select(func.count()).select_from(AppPreference))).scalar()
    assert count == 1  # fila única


async def test_idioma_no_soportado_422(client):
    r = await client.put("/preferences", json={"language": "fr"})
    assert r.status_code == 422 and r.json()["detail"] == "Idioma no soportado"
