"""Mensajes de huéspedes (feature 045, #186). Los textos nunca se guardan ni van a logs."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.errors import AuthError, ChannelError, RateLimited
from app.channels.factory import get_adapter, is_manual
from app.core.config import settings
from app.core.context import RequestContext, require_ctx
from app.db.session import get_session
from app.services import messages_service as svc

router = APIRouter()
log = logging.getLogger(__name__)

_UNAVAILABLE = "Beds24 no respondió. Intenta en unos minutos."


def _errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, svc.MessagesError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, AuthError):
        return HTTPException(status_code=422,
                             detail="Beds24 rechazó el acceso a los mensajes: reconecta Beds24 con "
                                    "permiso de escritura en bookings-personal.")
    if isinstance(exc, RateLimited):
        return HTTPException(status_code=429, detail="Beds24 está limitando las consultas. Intenta en unos minutos.")
    if isinstance(exc, ChannelError):
        return HTTPException(status_code=503, detail=_UNAVAILABLE)
    raise exc


async def _with_adapter(session: AsyncSession, fn):
    if is_manual(session):
        raise HTTPException(status_code=409, detail="Los mensajes requieren conectar Beds24.")
    adapter = get_adapter(session)
    try:
        if not svc.supports(adapter):
            raise HTTPException(status_code=409, detail="Tu conexión no permite mensajes.")
        try:
            return await fn(adapter)
        except (LookupError, svc.MessagesError, ChannelError) as exc:
            raise _errors(exc) from None
    finally:
        await adapter.aclose()


@router.get("")
async def inbox(session: AsyncSession = Depends(get_session)):
    if is_manual(session):
        return {"available": False, "conversations": [], "unread": 0}
    convs = await _with_adapter(session, lambda a: svc.inbox(session, a))
    return {"available": True, "conversations": convs, "unread": sum(c["unread"] for c in convs)}


@router.get("/{booking}")
async def thread(booking: str, session: AsyncSession = Depends(get_session)):
    return await _with_adapter(session, lambda a: svc.thread(session, a, booking))


class SendIn(BaseModel):
    text: str = Field(min_length=1, max_length=svc.MAX_TEXT)


@router.post("/{booking}")
async def send(booking: str, req: SendIn, session: AsyncSession = Depends(get_session),
               ctx: RequestContext = Depends(require_ctx)):
    await _with_adapter(session, lambda a: svc.send(session, a, booking, req.text))
    log.info("mensaje enviado: reserva=%s usuario=%s", booking, ctx.user_id)  # sin el texto
    return await _with_adapter(session, lambda a: svc.thread(session, a, booking))


@router.post("/{booking}/suggest")
async def suggest(booking: str, session: AsyncSession = Depends(get_session),
                  ctx: RequestContext = Depends(require_ctx)):
    """Borrador de respuesta (editable). Cuenta como un mensaje al asistente (027)."""
    from app.llm.client import default_llm
    from app.services import usage_service

    llm = default_llm()
    if llm is None:
        raise HTTPException(status_code=503, detail="La IA no está disponible en este momento.")
    quota = await usage_service.chat_quota(session, ctx.account_id)
    if quota.exhausted:
        raise HTTPException(status_code=429, detail="Llegaste al límite de mensajes al asistente de este mes.")
    await usage_service.record(session, usage_service.CHAT_MESSAGE)
    metered = usage_service.MeteredLLM(llm, session, usage_service.CHAT)
    out = await _with_adapter(session, lambda a: svc.suggest(session, a, metered, booking,
                                                             model=settings.llm_model))
    await session.commit()
    return {"text": out.text}
