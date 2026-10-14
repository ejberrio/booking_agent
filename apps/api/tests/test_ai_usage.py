"""Feature 027: uso y límites de IA por cuenta."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.routes import chat as chat_routes
from app.db.session import get_session
from app.db.tenancy import mark_platform, set_tenant
from app.llm.client import LLMResponse
from app.main import app
from app.models.account import Account
from app.models.agent import AgentAction, Conversation
from app.models.enums import AgentActionStatus
from app.models.usage import AIUsage
from app.search.base import SearchResult
from app.services import admin_service, usage_service

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 14)


class FakeLLM:
    def __init__(self, text="ok", usage=(1000, 200), model="gpt-6-luna"):
        self.text, self.usage, self.model, self.calls = text, usage, model, 0

    async def chat(self, *, messages, tools, model):
        self.calls += 1
        return LLMResponse(content=self.text, usage=self.usage, model=self.model)


class FakeSearch:
    def __init__(self):
        self.calls = 0

    async def search(self, query, *, max_results=5):
        self.calls += 1
        return [SearchResult(title=query, content="x")]


class _Adapter:
    async def aclose(self):
        return None


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    async def _override():
        yield session

    @asynccontextmanager
    async def fake_platform():
        async with session.info["maker"]() as s:
            mark_platform(s)
            yield s

    monkeypatch.setattr(admin_service, "platform_session", fake_platform)
    monkeypatch.setattr(chat_routes, "get_adapter", lambda *_a, **_k: _Adapter())
    monkeypatch.setattr(usage_service, "local_today", lambda now=None: TODAY)
    app.dependency_overrides[get_session] = _override
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


def test_costo_por_modelo_y_sin_precio():
    assert usage_service.llm_cost("openai/gpt-6-luna", 1_000_000, 1_000_000) == Decimal("0.6")
    assert usage_service.llm_cost("modelo-nuevo", 10, 10) is None
    assert usage_service.next_month(date(2026, 12, 5)) == date(2027, 1, 1)


async def test_el_chat_mide_mensajes_tokens_y_costo(client, session, monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(chat_routes, "default_llm", lambda: llm)
    r = await client.post("/chat", json={"message": "hola"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["quota"]["used"] == 1 and body["quota"]["limit"] == 300
    assert body["quota"]["resets_on"] == "2026-11-01" and body["limited"] is False
    rows = {u.kind: u for u in (await session.execute(select(AIUsage))).scalars()}
    assert rows["chat_message"].calls == 1
    assert rows["chat"].model == "gpt-6-luna" and rows["chat"].input_tokens == 1000
    assert rows["chat"].cost_usd == Decimal("0.0002")  # 1000×0.10/1M + 200×0.50/1M


async def test_limite_mensual_pausa_sin_llamar_a_la_ia(client, session, monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(chat_routes, "default_llm", lambda: llm)
    (await session.get(Account, 1)).chat_limit_month = 2
    await session.commit()
    first = (await client.post("/chat", json={"message": "uno"})).json()
    assert first["quota"]["warning"] is False
    second = (await client.post("/chat", json={"message": "dos",
                                               "conversation_id": first["conversation_id"]})).json()
    assert second["quota"]["exhausted"] is True and second["quota"]["warning"] is True
    third = (await client.post("/chat", json={"message": "tres", "language": "en",
                                              "conversation_id": first["conversation_id"]})).json()
    assert third["limited"] is True and "limit of 2" in third["reply"]
    assert llm.calls == 2  # el tercero no llamó a la IA
    # mes siguiente: vuelve a cero
    monkeypatch.setattr(usage_service, "local_today", lambda now=None: date(2026, 11, 1))
    fourth = (await client.post("/chat", json={"message": "cuatro"})).json()
    assert fourth["limited"] is False and fourth["quota"]["used"] == 1


async def test_con_accion_pendiente_la_confirmacion_no_se_bloquea(client, session, monkeypatch):
    llm = FakeLLM("Listo")
    monkeypatch.setattr(chat_routes, "default_llm", lambda: llm)
    (await session.get(Account, 1)).chat_limit_month = 0
    conv = Conversation()
    session.add(conv)
    await session.flush()
    session.add(AgentAction(conversation_id=conv.id, tool="set_price", arguments={},
                            status=AgentActionStatus.proposed))
    await session.commit()
    r = (await client.post("/chat", json={"message": "sí", "conversation_id": conv.id})).json()
    assert r["limited"] is False and llm.calls >= 1


async def test_busquedas_con_tope_diario(session):
    inner = FakeSearch()
    m = usage_service.MeteredSearch(inner, session, limit=2, day=TODAY)
    for q in ("a", "b", "c", "d"):
        await m.search(q)
    assert inner.calls == 2 and m.skipped == 2
    assert await usage_service.searches_on(session, TODAY) == 2
    # otro escaneo el mismo día no vuelve a buscar
    again = usage_service.MeteredSearch(inner, session, limit=2, day=TODAY)
    assert await again.search("e") == [] and inner.calls == 2


async def test_uso_aislado_por_cuenta(session, other_session):
    await usage_service.record(session, usage_service.SEARCH, day=TODAY)
    await session.commit()
    assert await usage_service.searches_on(other_session, TODAY) == 0
    assert await usage_service.searches_on(session, TODAY) == 1


async def test_panel_del_administrador_y_limites(client, session, other_session):
    await usage_service.record(session, usage_service.CHAT, model="gpt-6-luna",
                               input_tokens=500, output_tokens=100,
                               cost=usage_service.llm_cost("gpt-6-luna", 500, 100), day=TODAY)
    await usage_service.record(other_session, usage_service.SEARCH, cost=Decimal("0.008"), day=TODAY)
    await session.commit()
    await other_session.commit()
    data = (await client.get("/admin/usage?month=2026-10")).json()
    rows = {a["id"]: a for a in data["accounts"]}
    assert rows[1]["llm_calls"] == 1 and rows[1]["input_tokens"] == 500
    assert rows[2]["searches"] == 1 and data["total_cost_usd"] > 0
    assert set(rows[1]) >= {"chat_limit_month", "search_limit_day", "cost_usd"}
    r = await client.patch("/admin/accounts/2/limits", json={"chat_limit_month": 600})
    assert r.status_code == 200 and r.json()["chat_limit_month"] == 600
    async with session.info["maker"]() as s:
        set_tenant(s, 2)
        assert (await usage_service.chat_quota(s, 2, TODAY)).limit == 600
    r = await client.patch("/admin/accounts/2/limits", json={"chat_limit_month": None})
    assert r.json()["chat_limit_month"] is None


async def test_uso_de_la_cuenta_para_el_anfitrion(client, session):
    await usage_service.record(session, usage_service.CHAT_MESSAGE, day=TODAY)
    await session.commit()
    data = (await client.get("/account/usage")).json()
    assert data["chat"]["used"] == 1 and data["search"]["limit"] == 5
    assert "cost" not in str(data)
