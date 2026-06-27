"""Orquestador del agente: un turno de conversación con tool-calling.

Lectura → ejecuta; escritura → propone (AgentAction); confirmación → aplica vía 003
con origen=chat. La memoria es el historial de la conversación.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.property import Property, UnitType

MAX_STEPS = 6


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
    """Lista las unidades del host para que el agente no pregunte por IDs técnicos."""
    rows = (
        await session.execute(
            select(UnitType.id, UnitType.name, Property.id, Property.name)
            .join(Property, UnitType.property_id == Property.id)
            .order_by(UnitType.id)
        )
    ).all()
    if not rows:
        return ""
    if len(rows) == 1:
        uid, uname, pid, pname = rows[0]
        return (
            f"\n- El host tiene UNA sola unidad: unit_type_id={uid} «{uname}», "
            f"property_id={pid} («{pname}»). Usa esos identificadores en todas las "
            "herramientas SIN preguntar al host por IDs."
        )
    listing = "; ".join(f"unit_type_id={r[0]} «{r[1]}» (property_id={r[2]})" for r in rows)
    return f"\n- Unidades del host: {listing}. Usa el unit_type_id correcto sin preguntar por IDs."


async def _build_messages(session: AsyncSession, conversation_id: int) -> list[dict]:
    res = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    )
    system = system_prompt() + await _units_context(session)
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
) -> AgentReply:
    user_msg = await _persist(session, conversation_id, MessageRole.user, user_text)

    if llm is None:
        text = (
            "No hay un LLM configurado. Configura OPENAI_API_KEY en .env para activar el agente."
        )
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text)

    pending = await _pending_action(session, conversation_id)
    models = await _llm_models(session)
    model = models.actions if pending else models.general
    messages = await _build_messages(session, conversation_id)
    tools = openai_tools(include_control=pending is not None)
    events: list[dict] = []

    for _ in range(MAX_STEPS):
        resp = await llm.chat(messages=messages, tools=tools, model=model)

        if not resp.tool_calls:
            text = resp.content or ""
            await _persist(session, conversation_id, MessageRole.assistant, text)
            return AgentReply(text, events=events)

        tc = resp.tool_calls[0]
        events.append({"type": "tool", "name": tc.name})
        spec = ALL_TOOLS.get(tc.name)

        # Herramienta de lectura → ejecuta y realimenta.
        if spec and not spec.is_write and tc.name not in ("confirm_pending", "cancel_pending"):
            result = await exec_read(session, tc.name, tc.arguments)
            messages.append(
                {
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
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
            continue

        # Confirmación.
        if tc.name == "confirm_pending":
            return await _confirm(session, channel, conversation_id, pending, user_msg.id, events)

        # Cancelación.
        if tc.name == "cancel_pending":
            if pending:
                pending.status = AgentActionStatus.cancelled
                await session.flush()
            text = "Entendido, cancelo la propuesta."
            await _persist(session, conversation_id, MessageRole.assistant, text)
            return AgentReply(text, events=events)

        # Herramienta de escritura → proponer (no aplica).
        try:
            proposal = await build_proposal(session, tc.name, tc.arguments)
        except ValueError as exc:
            # Realimenta el error al LLM para que se corrija dentro del mismo turno
            # (p. ej. consultar el precio actual antes de proponer un porcentaje).
            messages.append(
                {
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
            )
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
        await _persist(session, conversation_id, MessageRole.assistant, proposal.summary)
        return AgentReply(proposal.summary, pending_action_id=action.id, events=events)

    text = "No pude completar la solicitud."
    await _persist(session, conversation_id, MessageRole.assistant, text)
    return AgentReply(text, events=events)


async def _confirm(
    session: AsyncSession,
    channel,
    conversation_id: int,
    pending: AgentAction | None,
    message_id: int,
    events: list[dict],
) -> AgentReply:
    if pending is None:
        text = "No hay ninguna propuesta pendiente para confirmar."
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text, events=events)

    outcome = await apply_proposal(session, channel, pending, message_id)

    if outcome.status == "stale":
        proposal = await build_proposal(session, pending.tool, pending.arguments)
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
        text = f"{outcome.summary} {proposal.summary}"
        await _persist(session, conversation_id, MessageRole.assistant, text)
        return AgentReply(text, pending_action_id=new_action.id, events=events)

    pending.status = AgentActionStatus.applied
    pending.applied_ref = outcome.applied_ref
    await session.flush()
    await _persist(session, conversation_id, MessageRole.assistant, outcome.summary)
    return AgentReply(outcome.summary, applied=True, events=events)
