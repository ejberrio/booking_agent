import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.llm.client import default_llm
from app.models.agent import Conversation

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


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
            session, adapter, default_llm(), conversation_id=conv_id, user_text=req.message
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
        session, adapter, default_llm(), conversation_id=conv_id, user_text=req.message
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
