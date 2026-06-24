from fastapi import APIRouter
from pydantic import BaseModel

from app.llm.client import complete

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Endpoint placeholder del agente.

    En la Fase 4 esto se convierte en el loop de tool-calling
    (get_prices, set_price, search_events, ...). Por ahora solo
    responde con el LLM configurado, o en modo demo si no hay API key.
    """
    reply = await complete(req.message)
    return ChatResponse(reply=reply)
