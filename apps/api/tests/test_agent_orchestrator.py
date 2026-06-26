from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.agent.orchestrator import run_turn
from app.channels.base import WriteResult
from app.llm.client import LLMResponse, ToolCall
from app.models.agent import AgentAction, Conversation, LLMConfig, Message
from app.models.audit import PriceChangeLog
from app.models.enums import AgentActionStatus, ChangeOrigin, ChannelKind, SuggestionStatus
from app.models.market import PriceSuggestion
from app.models.pricing import Promotion
from app.models.property import Channel, Property, UnitType
from app.services import pricing_service

D = Decimal
DAY = date(2026, 7, 15)


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def chat(self, *, messages, tools, model):
        self.calls.append({"messages": messages, "tools": tools, "model": model})
        return self.responses.pop(0)

    @property
    def models(self):
        return [c["model"] for c in self.calls]


class FakeCM:
    def __init__(self):
        self.published: list = []

    async def set_rate(self, room, day, price):
        return await self.set_rate_range(room, day, day, price)

    async def set_rate_range(self, room, df, dt, price):
        self.published.append((room, df, dt, price))
        return WriteResult(True, True)


def call(name, args):
    return LLMResponse(tool_calls=[ToolCall("c1", name, args)])


def final(text):
    return LLMResponse(content=text)


async def setup(session):
    conv = Conversation(title="t")
    session.add(conv)
    prop = Property(name="Casa")
    session.add(prop)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="r1")
    session.add(unit)
    await session.flush()
    return conv, prop, unit


async def _count(session, model) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_query_uses_tools_not_invented(session):
    conv, prop, unit = await setup(session)
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=DAY, new_price=D("180000"))
    llm = FakeLLM([
        call("get_calendar", {"unit_type_id": unit.id, "date_from": "2026-07-15", "date_to": "2026-07-15"}),
        final("El 15 de julio cuesta 180000 COP."),
    ])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="¿precio del 15?")
    assert "180000" in reply.text
    assert not llm.responses  # consumió la llamada de herramienta + respuesta final
    assert await _count(session, AgentAction) == 0


async def test_no_llm_config_message(session):
    conv, prop, unit = await setup(session)
    reply = await run_turn(session, FakeCM(), None, conversation_id=conv.id, user_text="hola")
    assert "No hay un LLM" in reply.text
    assert await _count(session, AgentAction) == 0


async def test_write_proposes_not_applies(session):
    conv, prop, unit = await setup(session)
    before = await _count(session, PriceChangeLog)
    llm = FakeLLM([
        call("propose_set_range", {"unit_type_id": unit.id, "date_from": "2026-07-15", "date_to": "2026-07-15", "price": 200000})
    ])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="pon 200000 el 15")
    assert reply.pending_action_id is not None
    assert reply.applied is False
    action = await session.get(AgentAction, reply.pending_action_id)
    assert action.status is AgentActionStatus.proposed
    assert await _count(session, PriceChangeLog) == before  # no aplicó


async def test_confirm_applies_origin_chat_and_links_message(session):
    conv, prop, unit = await setup(session)
    cm = FakeCM()
    llm1 = FakeLLM([call("propose_set_range", {"unit_type_id": unit.id, "date_from": "2026-07-15", "date_to": "2026-07-15", "price": 200000})])
    await run_turn(session, cm, llm1, conversation_id=conv.id, user_text="pon 200000 el 15")

    llm2 = FakeLLM([call("confirm_pending", {})])
    reply = await run_turn(session, cm, llm2, conversation_id=conv.id, user_text="sí")
    assert reply.applied is True
    assert await pricing_service.get_price(session, unit.id, DAY) == D("200000")
    log = (await session.execute(select(PriceChangeLog).where(PriceChangeLog.origin == ChangeOrigin.chat))).scalars().first()
    assert log is not None
    assert log.message_id is not None  # enlazado al mensaje de confirmación
    assert cm.published  # publicó el efectivo


async def test_confirm_stale_reproposes(session):
    conv, prop, unit = await setup(session)
    cm = FakeCM()
    llm1 = FakeLLM([call("propose_set_range", {"unit_type_id": unit.id, "date_from": "2026-07-15", "date_to": "2026-07-15", "price": 200000})])
    r1 = await run_turn(session, cm, llm1, conversation_id=conv.id, user_text="pon 200000 el 15")
    old_action_id = r1.pending_action_id

    # cambio externo del estado entre propuesta y confirmación
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=DAY, new_price=D("150000"))

    llm2 = FakeLLM([call("confirm_pending", {})])
    r2 = await run_turn(session, cm, llm2, conversation_id=conv.id, user_text="sí")
    assert r2.applied is False
    assert r2.pending_action_id is not None and r2.pending_action_id != old_action_id
    assert (await session.get(AgentAction, old_action_id)).status is AgentActionStatus.stale
    assert await pricing_service.get_price(session, unit.id, DAY) == D("150000")  # no se aplicó 200000


async def test_cancel_marks_cancelled(session):
    conv, prop, unit = await setup(session)
    llm1 = FakeLLM([call("propose_set_range", {"unit_type_id": unit.id, "date_from": "2026-07-15", "date_to": "2026-07-15", "price": 200000})])
    r1 = await run_turn(session, FakeCM(), llm1, conversation_id=conv.id, user_text="pon 200000 el 15")
    llm2 = FakeLLM([call("cancel_pending", {})])
    r2 = await run_turn(session, FakeCM(), llm2, conversation_id=conv.id, user_text="no, mejor no")
    assert r2.applied is False
    assert (await session.get(AgentAction, r1.pending_action_id)).status is AgentActionStatus.cancelled


async def test_reinforced_threshold(session):
    conv, prop, unit = await setup(session)
    llm = FakeLLM([call("propose_set_range", {"unit_type_id": unit.id, "date_from": "2026-07-01", "date_to": "2026-07-25", "price": 200000})])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="pon 200000 todo julio")
    action = await session.get(AgentAction, reply.pending_action_id)
    assert action.reinforced is True  # 25 días > 14


async def test_create_promotion_via_chat(session):
    conv, prop, unit = await setup(session)
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=DAY, new_price=D("180000"))
    cm = FakeCM()
    llm1 = FakeLLM([call("propose_create_promotion", {"property_id": prop.id, "name": "P10", "discount_type": "percent", "discount_value": 10, "start_date": "2026-07-15", "end_date": "2026-07-15"})])
    await run_turn(session, cm, llm1, conversation_id=conv.id, user_text="crea promo 10% el 15")
    llm2 = FakeLLM([call("confirm_pending", {})])
    reply = await run_turn(session, cm, llm2, conversation_id=conv.id, user_text="sí")
    assert reply.applied is True
    assert await _count(session, Promotion) == 1
    eff = await pricing_service.get_effective_price(session, prop.id, unit.id, DAY)
    assert eff == D("162000")  # 180000 - 10%


async def test_model_routing_general_vs_actions(session):
    conv, prop, unit = await setup(session)
    session.add(LLMConfig(model_general="g-model", model_actions="a-model"))
    await session.flush()
    llm1 = FakeLLM([call("propose_set_range", {"unit_type_id": unit.id, "date_from": "2026-07-15", "date_to": "2026-07-15", "price": 200000})])
    await run_turn(session, FakeCM(), llm1, conversation_id=conv.id, user_text="pon 200000 el 15")
    assert llm1.models == ["g-model"]  # sin pendiente -> general

    llm2 = FakeLLM([call("confirm_pending", {})])
    await run_turn(session, FakeCM(), llm2, conversation_id=conv.id, user_text="sí")
    assert llm2.models == ["a-model"]  # con pendiente -> acciones


async def test_get_suggestions_tool(session):
    conv, prop, unit = await setup(session)
    session.add(
        PriceSuggestion(
            property_id=prop.id, unit_type_id=unit.id,
            date_from=date(2026, 8, 5), date_to=date(2026, 8, 5),
            suggested_price=D("234000"), rationale={"text": "Feria de las Flores"},
            confidence=D("0.9"), status=SuggestionStatus.proposed,
        )
    )
    await session.flush()
    llm = FakeLLM([
        call("get_suggestions", {"date_from": "2026-08-01", "date_to": "2026-08-31"}),
        final("Te sugiero subir el 5 de agosto a 234000 COP por la Feria de las Flores."),
    ])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="¿qué me sugieres para agosto?")
    assert "234000" in reply.text


async def test_memory_includes_history(session):
    conv, prop, unit = await setup(session)
    llm1 = FakeLLM([final("Hola, ¿en qué te ayudo?")])
    await run_turn(session, FakeCM(), llm1, conversation_id=conv.id, user_text="hola soy el host")
    llm2 = FakeLLM([final("Claro.")])
    await run_turn(session, FakeCM(), llm2, conversation_id=conv.id, user_text="y el precio?")
    # el segundo turno recibió el historial (incluye el primer mensaje del host)
    contents = [m.get("content") for m in llm2.calls[0]["messages"]]
    assert "hola soy el host" in contents
    assert await _count(session, Message) >= 4  # 2 user + 2 assistant
