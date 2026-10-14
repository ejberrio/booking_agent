import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.api.routes.sync import get_adapter
from app.core.context import RequestContext, require_ctx
from app.db.session import get_session
from app.llm.client import default_llm
from app.models.agent import AgentAction, Conversation, Message
from app.models.enums import AgentActionStatus, MessageRole

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
    # Idioma del host (feature 021): el asistente responde en él.
    language: Literal["es", "en", "pt"] = "es"


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    pending_action_id: int | None = None
    applied: bool = False
    # Feature 027: mensajes del mes (used/limit/resets_on/warning/exhausted).
    quota: dict | None = None
    limited: bool = False
    # Feature 032: la propuesta pendiente con su vista previa estructurada (tabla en la web).
    pending_action: dict | None = None


_LIMIT_TEXT = {
    "es": "Alcanzaste el límite de {limit} mensajes al asistente de este mes. Se renueva el {date}. "
          "Las sugerencias diarias y aprobar o rechazar cambios siguen funcionando.",
    "en": "You reached this month's limit of {limit} assistant messages. It renews on {date}. "
          "Daily suggestions and approving or rejecting changes keep working.",
    "pt": "Você atingiu o limite de {limit} mensagens ao assistente deste mês. Ele renova em {date}. "
          "As sugestões diárias e aprovar ou rejeitar mudanças continuam funcionando.",
}


@dataclass
class _Turn:
    text: str
    pending_action_id: int | None = None
    applied: bool = False
    events: list = field(default_factory=list)
    limited: bool = False
    pending_action: dict | None = None


async def _metered_turn(
    session: AsyncSession, adapter, ctx: RequestContext, conv_id: int, req: ChatRequest
) -> tuple[_Turn, dict]:
    """Un turno del asistente respetando el límite mensual de la cuenta (feature 027).

    Con una acción pendiente de confirmar NO se bloquea: la respuesta del anfitrión (sí/no)
    siempre se atiende (principio III). Al límite y sin pendiente, no se llama a la IA.
    """
    from app.agent.orchestrator import _pending_action, _persist
    from app.services import usage_service

    quota = await usage_service.chat_quota(session, ctx.account_id)
    pending = await _pending_action(session, conv_id)
    if quota.exhausted and pending is None:
        text = _LIMIT_TEXT.get(req.language, _LIMIT_TEXT["es"]).format(
            limit=quota.limit, date=quota.resets_on.strftime("%d/%m/%Y")
        )
        await _persist(session, conv_id, MessageRole.user, req.message)
        await _persist(session, conv_id, MessageRole.assistant, text)
        return _Turn(text, limited=True), quota.as_dict()
    await usage_service.record(session, usage_service.CHAT_MESSAGE)
    llm = default_llm()
    metered = usage_service.MeteredLLM(llm, session, usage_service.CHAT) if llm else None
    reply = await run_turn(
        session, adapter, metered, conversation_id=conv_id,
        user_text=req.message, language=req.language,
    )
    quota.used += 1
    return (
        _Turn(reply.text, reply.pending_action_id, reply.applied, list(reply.events),
              pending_action=await _action_view(session, reply.pending_action_id)),
        quota.as_dict(),
    )


async def _action_view(session: AsyncSession, action_id: int | None) -> dict | None:
    if action_id is None:
        return None
    action = await session.get(AgentAction, action_id)
    if action is None or action.status != AgentActionStatus.proposed:
        return None
    return {"id": action.id, "tool": action.tool, "preview": action.preview,
            "reinforced": action.reinforced}


async def _ensure_conversation(session: AsyncSession, conversation_id: int | None) -> int:
    if conversation_id is not None:
        # Feature 026: una conversación de otra cuenta "no existe" (filtro por cuenta).
        if await session.get(Conversation, conversation_id) is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return conversation_id
    conv = Conversation()
    session.add(conv)
    await session.flush()
    return conv.id


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_ctx),
):
    adapter = get_adapter(session)
    try:
        conv_id = await _ensure_conversation(session, req.conversation_id)
        reply, quota = await _metered_turn(session, adapter, ctx, conv_id, req)
        await session.commit()
        return ChatResponse(
            reply=reply.text,
            conversation_id=conv_id,
            pending_action_id=reply.pending_action_id,
            applied=reply.applied,
            quota=quota,
            limited=reply.limited,
            pending_action=reply.pending_action,
        )
    finally:
        await adapter.aclose()


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_ctx),
):
    """Streaming SSE: emite el estado de las herramientas y el resultado final."""
    adapter = get_adapter(session)
    conv_id = await _ensure_conversation(session, req.conversation_id)
    try:
        reply, quota = await _metered_turn(session, adapter, ctx, conv_id, req)
        await session.commit()
    finally:
        await adapter.aclose()

    async def event_stream() -> AsyncIterator[str]:
        for ev in reply.events:
            yield f"event: tool\ndata: {json.dumps(ev)}\n\n"
        done = {
            "reply": reply.text,
            "conversation_id": conv_id,
            "pending_action_id": reply.pending_action_id,
            "applied": reply.applied,
            "quota": quota,
            "limited": reply.limited,
            "pending_action": reply.pending_action,
        }
        yield f"event: done\ndata: {json.dumps(done)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --------- Historial (feature 024: chat flotante + continuidad) ---------

_VISIBLE = (MessageRole.user, MessageRole.assistant)
TITLE_MAX = 60


def _title(conv: Conversation, first_user_text: str | None) -> str:
    if conv.title:
        return conv.title
    text = " ".join((first_user_text or "").split())
    return text if len(text) <= TITLE_MAX else text[: TITLE_MAX - 1].rstrip() + "…"


async def _first_user_text(session: AsyncSession, conversation_id: int) -> str | None:
    return (
        await session.execute(
            select(Message.content)
            .where(Message.conversation_id == conversation_id, Message.role == MessageRole.user)
            .order_by(Message.id)
            .limit(1)
        )
    ).scalar_one_or_none()


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(20, ge=1, le=50), session: AsyncSession = Depends(get_session)
):
    """Conversaciones recientes con al menos un mensaje del host (más reciente primero)."""
    last = func.max(Message.created_at).label("last")
    visible = func.count(Message.id).label("n")
    rows = (
        await session.execute(
            select(Message.conversation_id, last, visible)
            .where(Message.role.in_(_VISIBLE))
            .group_by(Message.conversation_id)
            .having(func.sum(case((Message.role == MessageRole.user, 1), else_=0)) > 0)
            .order_by(last.desc(), Message.conversation_id.desc())
            .limit(limit)
        )
    ).all()
    out = []
    for conv_id, last_at, n in rows:
        conv = await session.get(Conversation, conv_id)
        if conv is None:
            continue
        out.append(
            {
                "id": conv_id,
                "title": _title(conv, await _first_user_text(session, conv_id)),
                "updated_at": last_at,
                "message_count": int(n),
            }
        )
    return out


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, session: AsyncSession = Depends(get_session)):
    """Mensajes visibles (host/asistente) y propuesta pendiente de una conversación."""
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"No existe la conversación {conversation_id}")
    msgs = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role.in_(_VISIBLE))
            .order_by(Message.id)
        )
    ).scalars().all()
    pending = (
        await session.execute(
            select(AgentAction.id)
            .where(
                AgentAction.conversation_id == conversation_id,
                AgentAction.status == AgentActionStatus.proposed,
            )
            .order_by(AgentAction.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    first_user = next((m.content for m in msgs if m.role is MessageRole.user), None)
    return {
        "id": conv.id,
        "title": _title(conv, first_user),
        "messages": [
            {
                "role": "user" if m.role is MessageRole.user else "agent",
                "text": m.content,
                "created_at": m.created_at,
            }
            for m in msgs
        ],
        "pending_action_id": pending,
        "pending_action": await _action_view(session, pending),
    }


# --------- botones Confirmar / Cancelar (feature 032) ---------


class ActionRequest(BaseModel):
    conversation_id: int
    language: Literal["es", "en", "pt"] = "es"


async def _resolve(action_id: int, req: ActionRequest, session: AsyncSession, confirm: bool):
    from app.agent.orchestrator import resolve_action

    # Sin llamar a la IA ni contar mensajes de la cuota (#144).
    adapter = get_adapter(session)
    try:
        conv_id = await _ensure_conversation(session, req.conversation_id)
        reply = await resolve_action(
            session, adapter, conversation_id=conv_id, action_id=action_id,
            confirm=confirm, language=req.language,
        )
        await session.commit()
    finally:
        await adapter.aclose()
    return ChatResponse(
        reply=reply.text,
        conversation_id=conv_id,
        pending_action_id=reply.pending_action_id,
        applied=reply.applied,
        pending_action=await _action_view(session, reply.pending_action_id),
    )


@router.post("/actions/{action_id}/confirm", response_model=ChatResponse)
async def confirm_action(
    action_id: int, req: ActionRequest, session: AsyncSession = Depends(get_session)
):
    return await _resolve(action_id, req, session, True)


@router.post("/actions/{action_id}/cancel", response_model=ChatResponse)
async def cancel_action(
    action_id: int, req: ActionRequest, session: AsyncSession = Depends(get_session)
):
    return await _resolve(action_id, req, session, False)
