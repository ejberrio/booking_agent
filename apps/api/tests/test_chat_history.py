"""Feature 024: historial de conversaciones (chat flotante + continuidad)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio

from app.db.session import get_session
from app.main import app
from app.models.agent import AgentAction, Conversation, Message
from app.models.enums import AgentActionStatus, MessageRole
from sqlalchemy import update

pytestmark = pytest.mark.anyio

T0 = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _conv(session, msgs, minutes=0, title=None):
    c = Conversation(title=title)
    session.add(c)
    await session.flush()
    for i, (role, text) in enumerate(msgs):
        session.add(
            Message(
                conversation_id=c.id, role=role, content=text,
                created_at=T0 + timedelta(minutes=minutes, seconds=i),
            )
        )
    await session.flush()
    return c


async def test_lista_ordenada_con_titulo_y_sin_vacias(client, session):
    long = "¿Cuánto debería cobrar el 14 de noviembre si hay concierto de Juanes en el estadio?"
    a = await _conv(session, [(MessageRole.user, long), (MessageRole.assistant, "Te sugiero 470.000")], 0)
    b = await _conv(session, [(MessageRole.user, "Hola"), (MessageRole.tool, "{}"), (MessageRole.assistant, "¡Hola!")], 10)
    await _conv(session, [(MessageRole.system, "x")], 20)  # sin mensajes del host → no aparece
    await _conv(session, [], 30)
    await session.commit()

    data = (await client.get("/chat/conversations")).json()
    assert [c["id"] for c in data] == [b.id, a.id]
    assert data[0]["message_count"] == 2  # tool no cuenta
    assert len(data[1]["title"]) <= 60 and data[1]["title"].endswith("…")
    assert (await client.get("/chat/conversations", params={"limit": 1})).json()[0]["id"] == b.id
    assert (await client.get("/chat/conversations", params={"limit": 0})).status_code == 422


async def test_detalle_solo_visibles_y_propuesta_pendiente(client, session):
    c = await _conv(session, [
        (MessageRole.user, "Baja el 20 a 250.000"),
        (MessageRole.tool, '{"ok": true}'),
        (MessageRole.system, "interno"),
        (MessageRole.assistant, "Propuesta: 20 oct → 250.000. ¿Confirmas?"),
    ], title=None)
    session.add_all([
        AgentAction(conversation_id=c.id, tool="set_price", arguments={}, status=AgentActionStatus.cancelled),
        AgentAction(conversation_id=c.id, tool="set_price", arguments={}, status=AgentActionStatus.proposed),
    ])
    await session.commit()
    d = (await client.get(f"/chat/conversations/{c.id}")).json()
    assert [m["role"] for m in d["messages"]] == ["user", "agent"]
    assert d["title"] == "Baja el 20 a 250.000"
    pend = (await client.get(f"/chat/conversations/{c.id}")).json()["pending_action_id"]
    assert pend is not None

    # aplicada → ya no hay pendiente
    await session.execute(update(AgentAction).values(status=AgentActionStatus.applied))
    await session.commit()
    assert (await client.get(f"/chat/conversations/{c.id}")).json()["pending_action_id"] is None


async def test_titulo_propio_y_404(client, session):
    c = await _conv(session, [(MessageRole.user, "hola")], title="Precios de diciembre")
    await session.commit()
    assert (await client.get(f"/chat/conversations/{c.id}")).json()["title"] == "Precios de diciembre"
    r = await client.get("/chat/conversations/99999")
    assert r.status_code == 404 and r.json()["detail"] == "No existe la conversación 99999"
