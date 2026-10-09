import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.api.routes.sync import get_adapter
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


async def _ensure_conversation(session: AsyncSession, conversation_id: int | None) -> int:
    if conversation_id is not None:
        return conversation_id
    conv = Conversation()
    session.add(conv)
    await session.flush()
    return conv.id


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        conv_id = await _ensure_conversation(session, req.conversation_id)
        reply = await run_turn(
            session, adapter, default_llm(), conversation_id=conv_id,
            user_text=req.message,
            language=req.language,
        )
        await session.commit()
        return ChatResponse(
            reply=reply.text,
            conversation_id=conv_id,
            pending_action_id=reply.pending_action_id,
            applied=reply.applied,
        )
    finally:
        await adapter.aclose()


@router.post("/stream")
async def chat_stream(req: ChatRequest, session: AsyncSession = Depends(get_session)):
    """Streaming SSE: emite el estado de las herramientas y el resultado final."""
    adapter = get_adapter()
    conv_id = await _ensure_conversation(session, req.conversation_id)
    reply = await run_turn(
        session, adapter, default_llm(), conversation_id=conv_id,
        user_text=req.message,
        language=req.language,
    )
    await session.commit()
    await adapter.aclose()

    async def event_stream() -> AsyncIterator[str]:
        for ev in reply.events:
            yield f"event: tool\ndata: {json.dumps(ev)}\n\n"
        done = {
            "reply": reply.text,
            "conversation_id": conv_id,
            "pending_action_id": reply.pending_action_id,
            "applied": reply.applied,
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
    }
