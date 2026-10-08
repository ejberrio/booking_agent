"""Avisos entrantes de Beds24 (feature 020).

`POST /hooks/beds24` llega desde la entrada pública de la web (sin sesión); el resto
pasa por el proxy con sesión. Ninguna respuesta ni log contiene el cuerpo del aviso,
datos del huésped ni la clave (salvo la línea de `POST /hooks/beds24/key`, una vez).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.services import webhook_service

router = APIRouter()


@router.post("/beds24")
async def beds24_booking_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    check = webhook_service.verify_key(request.headers.get(webhook_service.HEADER_NAME))
    if check == "missing_config":
        raise HTTPException(status_code=503, detail="Avisos no configurados")
    if check == "invalid":
        await webhook_service.record_rejected(session)
        await session.commit()
        raise HTTPException(status_code=401, detail="No autorizado")

    hint = webhook_service.parse_hint(await request.body())
    adapter = get_adapter()
    try:
        event = await webhook_service.handle(session, adapter, hint)
        await session.commit()
        # 200 también si el re-sync falló: reintentar contra el mismo Beds24 caído no
        # ayuda; queda registrado y el cron diario lo corrige.
        return {"result": event.result.value}
    finally:
        await adapter.aclose()


@router.get("/beds24/status")
async def beds24_status(session: AsyncSession = Depends(get_session)):
    return await webhook_service.status(session)


@router.post("/beds24/key")
async def beds24_generate_key(session: AsyncSession = Depends(get_session)):
    line, hint = await webhook_service.generate_key(session)
    await session.commit()
    return {"header_line": line, "hint": hint}
