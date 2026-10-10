"""Avisos entrantes de Beds24 (feature 020).

`POST /hooks/beds24` llega desde la entrada pública de la web (sin sesión); el resto
pasa por el proxy con sesión. Ninguna respuesta ni log contiene el cuerpo del aviso,
datos del huésped ni la clave (salvo la línea de `POST /hooks/beds24/key`, una vez).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.core.context import require_ctx
from app.db.session import get_session
from app.db.tenancy import set_tenant
from app.services import webhook_service

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/beds24")
async def beds24_booking_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    check, account_id = webhook_service.resolve_key(
        request.headers.get(webhook_service.HEADER_NAME)
    )
    if check == "missing_config":
        raise HTTPException(status_code=503, detail="Avisos no configurados")
    if check == "invalid" or account_id is None:
        # Clave de ninguna cuenta: no hay cuenta donde registrarlo (feature 026).
        log.warning("webhook beds24: clave no reconocida")
        raise HTTPException(status_code=401, detail="No autorizado")
    # La clave identifica la cuenta: todo lo que sigue ocurre SOLO en ella.
    set_tenant(session, account_id)

    hint = webhook_service.parse_hint(await request.body())
    adapter = get_adapter(session)
    try:
        event = await webhook_service.handle(session, adapter, hint)
        await session.commit()
        # 200 también si el re-sync falló: reintentar contra el mismo Beds24 caído no
        # ayuda; queda registrado y el cron diario lo corrige.
        return {"result": event.result.value}
    finally:
        await adapter.aclose()


@router.get("/beds24/status", dependencies=[Depends(require_ctx)])
async def beds24_status(session: AsyncSession = Depends(get_session)):
    return await webhook_service.status(session)


@router.post("/beds24/key", dependencies=[Depends(require_ctx)])
async def beds24_generate_key(session: AsyncSession = Depends(get_session)):
    line, hint = await webhook_service.generate_key(session)
    await session.commit()
    return {"header_line": line, "hint": hint}
