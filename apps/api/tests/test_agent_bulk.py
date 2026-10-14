"""Feature 032: el asistente cambia varias noches con UNA propuesta y UNA confirmación."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.agent import tools
from app.agent.orchestrator import resolve_action, run_turn
from app.channels.base import FixedPriceWriteResult, RemoteRate, WriteResult
from app.core.config import settings
from app.llm.client import LLMResponse, ToolCall
from app.models.agent import AgentAction, Conversation
from app.models.booking import Booking
from app.models.enums import AgentActionStatus, ChannelKind, SuggestionStatus
from app.models.market import PriceSuggestion
from app.models.pricing import Promotion
from app.models.property import Channel, Property, UnitType
from app.services import pricing_service

pytestmark = pytest.mark.anyio

D = Decimal
START = date.today() + timedelta(days=30)


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def chat(self, *, messages, tools, model):
        self.calls += 1
        return self.responses.pop(0)


class FakeCM:
    def __init__(self):
        self.published: list = []
        self.fixed: list = []

    async def set_rate(self, room, day, price):
        return await self.set_rate_range(room, day, day, price)

    async def set_rate_range(self, room, df, dt, price):
        self.published.append((df, dt, price))
        return WriteResult(True, True)

    async def get_rates(self, room, df, dt):
        return [RemoteRate(room, df, D("300000"), 1)]

    async def set_fixed_price(self, fp):
        self.fixed.append(fp)
        return FixedPriceWriteResult(ok=True, verified=True, external_id=900 + len(self.fixed))

    async def disable_fixed_price(self, external_id, room):
        return FixedPriceWriteResult(ok=True, verified=True, external_id=external_id)

    async def aclose(self):
        return None


def calls(*pairs):
    return LLMResponse(tool_calls=[ToolCall(f"c{i}", n, a) for i, (n, a) in enumerate(pairs)])


def final(text):
    return LLMResponse(content=text)


@pytest.fixture(autouse=True)
def _offer(monkeypatch):
    monkeypatch.setattr(settings, "beds24_promo_offer_id", 3)


async def setup(session, prices: list[int]):
    conv = Conversation(title="t")
    prop = Property(name="Casa", currency="COP")
    session.add_all([conv, prop])
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    unit = UnitType(property_id=prop.id, name="Apto", units_count=1, external_ref="r1")
    session.add(unit)
    await session.flush()
    for i, p in enumerate(prices):
        await pricing_service.set_base_price(
            session, unit_type_id=unit.id, day=START + timedelta(days=i), new_price=D(p)
        )
    return conv, unit


def _day(i: int) -> str:
    return (START + timedelta(days=i)).isoformat()


async def _price(session, unit, i):
    return await pricing_service.get_price(session, unit.id, START + timedelta(days=i))


async def test_subir_porcentaje_en_bloque_con_precios_distintos(session):
    conv, unit = await setup(session, [300000, 320000, 350000, 300000, 310000])
    # la noche 2 está reservada: se omite
    session.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking,
                        check_in=START + timedelta(days=2), check_out=START + timedelta(days=3)))
    await session.flush()
    llm = FakeLLM([calls(("propose_price_change", {
        "unit_type_id": unit.id, "mode": "percent", "value": 10,
        "date_from": _day(0), "date_to": _day(4),
    }))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id,
                           user_text="sube 10% esas fechas")
    assert reply.pending_action_id is not None
    action = await session.get(AgentAction, reply.pending_action_id)
    assert action.preview["kind"] == "price" and action.preview["totals"]["affected"] == 4
    assert action.preview["totals"]["skipped"] == {"reservada": 1}
    news = {r["from"]: r["new"] for r in action.preview["rows"]}
    assert news[_day(0)] == "330000" and news[_day(1)] == "352000"
    # nada cambió todavía
    assert await _price(session, unit, 0) == D("300000")

    cm = FakeCM()
    done = await resolve_action(session, cm, conversation_id=conv.id,
                                action_id=action.id, confirm=True)
    assert done.applied is True and "4" in done.text
    assert [await _price(session, unit, i) for i in range(5)] == [
        D("330000"), D("352000"), D("350000"), D("330000"), D("341000")
    ]
    assert cm.published  # se publicó al canal
    assert (await session.get(AgentAction, action.id)).status == AgentActionStatus.applied


async def test_fin_de_semana_y_fechas_sueltas(session):
    conv, unit = await setup(session, [300000] * 14)
    prop = await tools.build_proposal(session, "propose_price_change", {
        "unit_type_id": unit.id, "mode": "set", "value": 400000,
        "date_from": _day(0), "date_to": _day(13), "weekdays": [4, 5],
    })
    assert prop.preview["totals"]["affected"] == 4  # 2 viernes + 2 sábados
    prop2 = await tools.build_proposal(session, "propose_price_change", {
        "unit_type_id": unit.id, "mode": "amount", "value": -20000,
        "dates": [_day(1), _day(7)], "round_to": 1000,
    }, "en")
    assert prop2.preview["totals"]["affected"] == 2 and "night(s)" in prop2.summary


async def test_limites_de_seguridad(session):
    conv, unit = await setup(session, [300000])
    with pytest.raises(ValueError):  # más de 366 noches
        await tools.build_proposal(session, "propose_price_change", {
            "unit_type_id": unit.id, "mode": "set", "value": 1,
            "date_from": _day(0), "date_to": _day(400),
        })
    with pytest.raises(ValueError):  # variación > 50 %: ninguna noche cambia
        await tools.build_proposal(session, "propose_price_change", {
            "unit_type_id": unit.id, "mode": "percent", "value": 80,
            "date_from": _day(0), "date_to": _day(0),
        })


async def test_huella_cambia_y_se_vuelve_a_proponer(session):
    conv, unit = await setup(session, [300000, 300000])
    llm = FakeLLM([calls(("propose_price_change", {
        "unit_type_id": unit.id, "mode": "percent", "value": 10,
        "date_from": _day(0), "date_to": _day(1),
    }))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="sube")
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=START, new_price=D(310000))
    again = await resolve_action(session, FakeCM(), conversation_id=conv.id,
                                 action_id=reply.pending_action_id, confirm=True)
    assert again.applied is False and again.pending_action_id not in (None, reply.pending_action_id)
    assert await _price(session, unit, 1) == D("300000")


async def test_lecturas_en_paralelo_y_una_sola_propuesta(session):
    conv, unit = await setup(session, [300000, 300000])
    llm = FakeLLM([
        calls(("get_calendar", {"unit_type_id": unit.id, "date_from": _day(0), "date_to": _day(1)}),
              ("get_offer_promotions", {"unit_type_id": unit.id})),
        calls(("propose_price_change", {"unit_type_id": unit.id, "mode": "set", "value": 310000,
                                        "dates": [_day(0)]}),
              ("propose_price_change", {"unit_type_id": unit.id, "mode": "set", "value": 310000,
                                        "dates": [_day(1)]})),
        calls(("propose_price_change", {"unit_type_id": unit.id, "mode": "set", "value": 310000,
                                        "dates": [_day(0), _day(1)]})),
    ])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="x")
    assert llm.calls == 3 and reply.pending_action_id is not None
    n = (await session.execute(select(func.count()).select_from(AgentAction))).scalar_one()
    assert n == 1


async def _suggestion(session, unit, i, j, price, status=SuggestionStatus.proposed):
    s = PriceSuggestion(unit_type_id=unit.id, property_id=unit.property_id,
                        date_from=START + timedelta(days=i), date_to=START + timedelta(days=j),
                        suggested_price=D(price), status=status, rationale={"text": "Evento"})
    session.add(s)
    await session.flush()
    return s


async def test_aplicar_sugerencias_desde_el_chat(session):
    conv, unit = await setup(session, [300000] * 6)
    up = await _suggestion(session, unit, 0, 1, 360000)
    other = await _suggestion(session, unit, 4, 5, 390000)
    llm = FakeLLM([calls(("propose_apply_suggestions", {"date_from": _day(0), "date_to": _day(2)}))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id,
                           user_text="aplica las sugerencias de esta semana")
    action = await session.get(AgentAction, reply.pending_action_id)
    assert action.arguments["suggestion_ids"] == [up.id]
    assert action.preview["kind"] == "apply_suggestions" and action.preview["totals"]["affected"] == 2
    done = await resolve_action(session, FakeCM(), conversation_id=conv.id,
                                action_id=action.id, confirm=True)
    assert done.applied is True
    assert (await session.get(PriceSuggestion, up.id)).status == SuggestionStatus.applied
    assert (await session.get(PriceSuggestion, other.id)).status == SuggestionStatus.proposed
    assert await _price(session, unit, 0) == D("360000")


async def test_rechazar_sugerencias_y_ids_inexistentes(session):
    conv, unit = await setup(session, [300000] * 4)
    a = await _suggestion(session, unit, 0, 0, 360000)
    b = await _suggestion(session, unit, 2, 2, 250000)
    prop = await tools.build_proposal(session, "propose_reject_suggestions", {"direction": "down"})
    assert prop.arguments["suggestion_ids"] == [b.id]
    with pytest.raises(ValueError):
        await tools.build_proposal(session, "propose_apply_suggestions", {"suggestion_ids": [99999]})
    llm = FakeLLM([calls(("propose_reject_suggestions", {"suggestion_ids": [a.id, b.id]}))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="recházalas")
    await resolve_action(session, FakeCM(), conversation_id=conv.id,
                         action_id=reply.pending_action_id, confirm=True)
    assert (await session.get(PriceSuggestion, a.id)).status == SuggestionStatus.rejected
    assert (await session.get(PriceSuggestion, b.id)).status == SuggestionStatus.rejected


async def test_descuento_por_dias_de_semana_en_tramos(session, monkeypatch):
    conv, unit = await setup(session, [300000] * 21)
    monkeypatch.setattr(tools, "get_adapter", lambda *_a, **_k: FakeCM())
    tuesdays = [i for i in range(21) if (START + timedelta(days=i)).weekday() == 1]
    llm = FakeLLM([calls(("propose_discount", {
        "unit_type_id": unit.id, "name": "Martes", "discount_pct": 15,
        "date_from": _day(0), "date_to": _day(20), "weekdays": [1],
    }))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="15% martes")
    action = await session.get(AgentAction, reply.pending_action_id)
    assert action.preview["kind"] == "discount"
    assert len(action.preview["rows"]) == len(tuesdays)  # un tramo por martes
    assert all(r["new"] == "255000" for r in action.preview["rows"])
    cm = FakeCM()
    done = await resolve_action(session, cm, conversation_id=conv.id,
                                action_id=action.id, confirm=True)
    assert done.applied is True
    promos = (await session.execute(select(Promotion))).scalars().all()
    assert len(promos) == len(tuesdays)
    # el precio base no cambió
    assert await _price(session, unit, tuesdays[0]) == D("300000")


async def test_cancelar_con_boton_y_accion_ajena(session):
    conv, unit = await setup(session, [300000])
    llm = FakeLLM([calls(("propose_price_change", {
        "unit_type_id": unit.id, "mode": "set", "value": 310000, "dates": [_day(0)],
    }))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="x")
    wrong = await resolve_action(session, FakeCM(), conversation_id=conv.id,
                                 action_id=reply.pending_action_id + 999, confirm=True)
    assert wrong.applied is False
    done = await resolve_action(session, FakeCM(), conversation_id=conv.id,
                                action_id=reply.pending_action_id, confirm=False)
    assert "cancel" in done.text.lower()
    assert (await session.get(AgentAction, reply.pending_action_id)).status == AgentActionStatus.cancelled
    assert await _price(session, unit, 0) == D("300000")


async def test_herramientas_viejas_ocultas_al_modelo():
    names = {t["function"]["name"] for t in tools.openai_tools(include_control=False)}
    assert "propose_price_change" in names and "propose_discount" in names
    assert not names & {"propose_set_day", "propose_set_range", "propose_create_promotion",
                        "propose_delete_promotion"}


async def test_botones_no_gastan_cuota_ni_llaman_a_la_ia(session, monkeypatch):
    import httpx

    from app.api.routes import chat as chat_routes
    from app.db.session import get_session
    from app.main import app
    from app.models.usage import AIUsage

    conv, unit = await setup(session, [300000])
    llm = FakeLLM([calls(("propose_price_change", {
        "unit_type_id": unit.id, "mode": "set", "value": 310000, "dates": [_day(0)],
    }))])
    reply = await run_turn(session, FakeCM(), llm, conversation_id=conv.id, user_text="x")
    await session.commit()

    def _no_llm():
        raise AssertionError("los botones no deben llamar a la IA")

    async def _override():
        yield session

    monkeypatch.setattr(chat_routes, "default_llm", _no_llm)
    monkeypatch.setattr(chat_routes, "get_adapter", lambda *_a, **_k: FakeCM())
    app.dependency_overrides[get_session] = _override
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as c:
            conv_data = (await c.get(f"/chat/conversations/{conv.id}")).json()
            assert conv_data["pending_action"]["preview"]["kind"] == "price"
            r = await c.post(f"/chat/actions/{reply.pending_action_id}/confirm",
                             json={"conversation_id": conv.id, "language": "pt"})
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert r.status_code == 200 and r.json()["applied"] is True
    assert "Pronto" in r.json()["reply"]
    used = (await session.execute(select(func.count()).select_from(AIUsage))).scalar_one()
    assert used == 0
    assert await _price(session, unit, 0) == D("310000")
