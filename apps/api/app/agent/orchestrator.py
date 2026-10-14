"""Orquestador del agente: un turno de conversación con tool-calling.

Lectura → ejecuta; escritura → propone (AgentAction); confirmación → aplica vía 003
con origen=chat. La memoria es el historial de la conversación.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import texts as agent_texts
from app.agent.prompts import system_prompt
from app.agent.tools import (
    ALL_TOOLS,
    apply_proposal,
    build_proposal,
    exec_read,
    openai_tools,
)
from app.core.config import settings
from app.llm.client import LLM
from app.models.agent import AgentAction, LLMConfig, Message
from app.models.enums import AgentActionStatus, MessageRole
from app.models.property import Channel, Property, UnitType

_MANUAL_NOTE = {
    "es": " Estás sin conexión: quedó registrado en StayLever; aplícalo a mano en Airbnb y "
          "Booking (Sugerencias y Ajustes tienen los enlaces).",
    "en": " You're offline: it's recorded in StayLever; apply it by hand on Airbnb and Booking "
          "(Suggestions and Settings have the links).",
    "pt": " Você está sem conexão: ficou registrado no StayLever; aplique à mão no Airbnb e no "
          "Booking (Sugestões e Configurações têm os links).",
}

MAX_STEPS = 10  # llamadas al modelo por turno (feature 032: antes 6)


@dataclass
class AgentReply:
    text: str
    pending_action_id: int | None = None
    applied: bool = False
    events: list[dict] = field(default_factory=list)


@dataclass
class _Models:
    general: str
    actions: str


async def _llm_models(session: AsyncSession) -> _Models:
    res = await session.execute(select(LLMConfig).where(LLMConfig.is_active.is_(True)))
    cfg = res.scalars().first()
    if cfg:
        return _Models(cfg.model_general, cfg.model_actions)
    return _Models(settings.llm_model, settings.llm_model_actions)


async def _pending_action(session: AsyncSession, conversation_id: int) -> AgentAction | None:
    res = await session.execute(
        select(AgentAction)
        .where(
            AgentAction.conversation_id == conversation_id,
            AgentAction.status == AgentActionStatus.proposed,
        )
        .order_by(AgentAction.id.desc())
    )
    return res.scalars().first()


_ROLE = {
    MessageRole.user: "user",
    MessageRole.assistant: "assistant",
    MessageRole.system: "system",
    MessageRole.tool: "user",
}


async def _units_context(session: AsyncSession) -> str:
    """Lista las unidades de la cuenta (filtro automático por cuenta, feature 026) con su
    ciudad y moneda, para que el agente no pregunte por IDs técnicos."""
    rows = (
        await session.execute(
            select(UnitType.id, UnitType.name, Property.id, Property.name, Property.city,
                   Property.currency)
            .join(Property, UnitType.property_id == Property.id)
            .order_by(UnitType.id)
        )
    ).all()
    if not rows:
        return (
            "\n- Esta cuenta aún no tiene unidades: explica que primero debe conectar su "
            "Channel Manager en Ajustes."
        )
    if len(rows) == 1:
        uid, uname, pid, pname, city, currency = rows[0]
        return (
            f"\n- El host tiene UNA sola unidad: unit_type_id={uid} «{uname}», "
            f"property_id={pid} («{pname}», {city}, moneda {currency}). Usa esos "
            "identificadores en todas las herramientas SIN preguntar al host por IDs."
        )
    listing = "; ".join(
        f"unit_type_id={r[0]} «{r[1]}» (property_id={r[2]}, {r[4]}, moneda {r[5]})" for r in rows
    )
    return f"\n- Unidades del host: {listing}. Usa el unit_type_id correcto sin preguntar por IDs."


async def _active_channels(session: AsyncSession) -> list[str]:
    """Tokens de los canales activos registrados (para el prompt multi-canal)."""
    rows = (
        await session.execute(
            select(Channel.kind).where(Channel.is_active.is_(True)).order_by(Channel.kind)
        )
    ).scalars()
    return [k.value for k in rows]


async def _build_messages(
    session: AsyncSession, conversation_id: int, language: str = "es"
) -> list[dict]:
    res = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    )
    system = system_prompt(
        active_channels=await _active_channels(session) or None, language=language
    ) + await _units_context(session)
    from app.channels.factory import is_manual

    if is_manual(session):
        system += (
            "\n- MODO SIN CONEXIÓN: esta cuenta no tiene Channel Manager. Tus propuestas solo "
            "actualizan los precios y la ocupación guardados en StayLever; NO se publican. Dilo "
            "al proponer y recuerda que el anfitrión debe aplicarlos a mano en Airbnb y Booking."
        )
    msgs = [{"role": "system", "content": system}]
    for m in res.scalars():
        msgs.append({"role": _ROLE.get(m.role, "user"), "content": m.content})
    return msgs


async def _persist(session: AsyncSession, conversation_id: int, role: MessageRole, content: str) -> Message:
    m = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(m)
    await session.flush()
    return m


async def run_turn(
    session: AsyncSession,
    channel,
    llm: LLM | None,
    *,
    conversation_id: int,
    user_text: str,
    language: str = "es",
) -> AgentReply:
    user_msg = await _persist(session, conversation_id, MessageRole.user, user_text)

    def tr(text: str) -> str:  # textos FIJOS al idioma del host (feature 021)
        return agent_texts.translate(text, language)

    if llm is None:
        text = tr(
            "No hay un LLM configurado. Configura OPENAI_API_KEY en .env para activar el agente."
        )
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text)

    pending = await _pending_action(session, conversation_id)
    models = await _llm_models(session)
    model = models.actions if pending else models.general
    messages = await _build_messages(session, conversation_id, language)
    tools = openai_tools(include_control=pending is not None)
    events: list[dict] = []

    def _echo(tc) -> dict:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
            ],
        }

    for _ in range(MAX_STEPS):
        resp = await llm.chat(messages=messages, tools=tools, model=model)

        if not resp.tool_calls:
            text = resp.content or ""
            await _persist(session, conversation_id, MessageRole.assistant, text)
            return AgentReply(text, events=events)

        # Feature 032: TODAS las lecturas de la respuesta se ejecutan (antes solo la
        # primera llamada); de escrituras se acepta UNA sola propuesta por turno.
        reads, controls, writes = [], [], []
        for tc in resp.tool_calls:
            events.append({"type": "tool", "name": tc.name})
            spec = ALL_TOOLS.get(tc.name)
            if tc.name in ("confirm_pending", "cancel_pending"):
                controls.append(tc)
            elif spec and not spec.is_write:
                reads.append(tc)
            else:
                writes.append(tc)

        if controls:
            if controls[0].name == "confirm_pending":
                return await _confirm(
                    session, channel, conversation_id, pending, user_msg.id, events, language
                )
            return await _cancel(session, conversation_id, pending, events, language)

        for tc in reads:
            result = await exec_read(session, tc.name, tc.arguments)
            messages.append(_echo(tc))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

        if not writes:
            continue
        if len(writes) > 1:
            msg = (
                "Solo se admite UNA propuesta por turno: combina todo en una sola llamada "
                "(usa date_from/date_to con weekdays o 'dates', o varias sugerencias por ids)."
            )
            for tc in writes:
                messages.append(_echo(tc))
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": json.dumps({"error": msg})}
                )
            continue

        tc = writes[0]
        try:
            proposal = await build_proposal(session, tc.name, tc.arguments, language)
        except ValueError as exc:
            # Realimenta el error al LLM para que se corrija dentro del mismo turno.
            messages.append(_echo(tc))
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": json.dumps({"error": str(exc)})}
            )
            continue
        if pending:
            pending.status = AgentActionStatus.cancelled
        action = AgentAction(
            conversation_id=conversation_id,
            message_id=user_msg.id,
            tool=proposal.tool,
            arguments=proposal.arguments,
            preview=proposal.preview,
            fingerprint=proposal.fingerprint,
            reinforced=proposal.reinforced,
            status=AgentActionStatus.proposed,
        )
        session.add(action)
        await session.flush()
        summary = tr(proposal.summary)
        await _persist(session, conversation_id, MessageRole.assistant, summary)
        return AgentReply(summary, pending_action_id=action.id, events=events)

    text = tr("No pude completar la solicitud.")
    await _persist(session, conversation_id, MessageRole.assistant, text)
    return AgentReply(text, events=events)


async def _confirm(
    session: AsyncSession,
    channel,
    conversation_id: int,
    pending: AgentAction | None,
    message_id: int,
    events: list[dict],
    language: str = "es",
) -> AgentReply:
    def tr(text: str) -> str:
        return agent_texts.translate(text, language)

    if pending is None:
        text = tr("No hay ninguna propuesta pendiente para confirmar.")
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text, events=events)

    outcome = await apply_proposal(session, channel, pending, message_id, language)

    if outcome.status == "stale":
        proposal = await build_proposal(session, pending.tool, pending.arguments, language)
        pending.status = AgentActionStatus.stale
        new_action = AgentAction(
            conversation_id=conversation_id,
            message_id=message_id,
            tool=proposal.tool,
            arguments=proposal.arguments,
            preview=proposal.preview,
            fingerprint=proposal.fingerprint,
            reinforced=proposal.reinforced,
            status=AgentActionStatus.proposed,
        )
        session.add(new_action)
        await session.flush()
        text = f"{tr(outcome.summary)} {tr(proposal.summary)}"
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text, pending_action_id=new_action.id, events=events)

    pending.status = AgentActionStatus.applied
    pending.applied_ref = outcome.applied_ref
    await session.flush()
    done = tr(outcome.summary)
    if getattr(channel, "manual", False):
        # Modo sin conexión (feature 029): nada se publicó; el anfitrión lo aplica a mano.
        done += _MANUAL_NOTE.get(language, _MANUAL_NOTE["es"])
    await _persist(session, conversation_id, MessageRole.assistant, done)
    return AgentReply(done, applied=True, events=events)


async def _cancel(
    session: AsyncSession,
    conversation_id: int,
    pending: AgentAction | None,
    events: list[dict],
    language: str = "es",
) -> AgentReply:
    if pending:
        pending.status = AgentActionStatus.cancelled
        await session.flush()
    text = agent_texts.translate("Entendido, cancelo la propuesta.", language)
    await _persist(session, conversation_id, MessageRole.assistant, text)
    return AgentReply(text, events=events)


async def resolve_action(
    session: AsyncSession,
    channel,
    *,
    conversation_id: int,
    action_id: int,
    confirm: bool,
    language: str = "es",
) -> AgentReply:
    """Botones Confirmar/Cancelar (feature 032): sin modelo de lenguaje ni cuota.

    Solo actúa sobre la propuesta PENDIENTE de esa conversación (de la cuenta del contexto,
    por el filtro automático); cualquier otra cosa responde "no hay propuesta pendiente".
    """
    pending = await _pending_action(session, conversation_id)
    label = "Confirmar" if confirm else "Cancelar"
    msg = await _persist(session, conversation_id, MessageRole.user, f"[{label}]")
    if pending is None or pending.id != action_id:
        text = agent_texts.translate("No hay ninguna propuesta pendiente para confirmar.", language)
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text)
    if confirm:
        return await _confirm(session, channel, conversation_id, pending, msg.id, [], language)
    return await _cancel(session, conversation_id, pending, [], language)
