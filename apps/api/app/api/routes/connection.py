"""Asistente «Conectar Beds24» (feature 044, #150).

Pasos: canjear el código de invitación y validar → elegir propiedades y habitaciones →
importar (reutiliza `POST /sync/import`). El token nunca sale del servidor ni va a logs.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import get_adapter, is_manual
from app.core.config import settings
from app.core.context import RequestContext, require_ctx
from app.db.cross_account import property_taken_elsewhere
from app.db.tenancy import current_account_id
from app.db.session import get_session
from app.services import connection_service, secret_service, sync_service

router = APIRouter()

_UNAVAILABLE = "Beds24 no respondió (servicio no disponible o error de red). Intenta en unos minutos."


async def _require_owner(session: AsyncSession, ctx: RequestContext) -> None:
    """Solo el dueño de la cuenta conecta o cambia la selección (modo sin usuarios: el host)."""
    if ctx.user_id is None:
        return
    from app.models.auth import Membership

    role = (
        await session.execute(
            select(Membership.role).where(Membership.user_id == ctx.user_id,
                                          Membership.account_id == ctx.account_id)
        )
    ).scalar_one_or_none()
    if role != "owner":
        raise HTTPException(status_code=403, detail="Solo el dueño de la cuenta puede conectar Beds24")


async def _rooms(session: AsyncSession) -> dict:
    """Propiedades y habitaciones de la cuenta de Beds24, con lo elegido y lo que es de otra
    cuenta (deshabilitado). Una llamada a Beds24. En modo sin conexión trae además los
    apartamentos manuales para asociarlos (entrega 2)."""
    adapter = _adapter(session)
    try:
        props = await adapter.get_properties()
    finally:
        await adapter.aclose()
    selected = await connection_service.selected_rooms(session)
    out = []
    for p in props:
        taken = await property_taken_elsewhere(session, "beds24", str(p.external_id))
        out.append({
            "id": str(p.external_id), "name": p.name, "currency": p.currency,
            "taken": taken,
            "rooms": [{"id": str(r.external_id), "name": r.name, "units": r.units_count,
                       "selected": not taken and (selected is None or str(r.external_id) in selected)}
                      for r in p.rooms],
        })
    manual = await connection_service.manual_units(session) if is_manual(session) else []
    return {"properties": out, "all": selected is None, "manual_units": manual}


def _adapter(session: AsyncSession):
    """El de Beds24 aunque la cuenta siga en modo sin conexión (el asistente necesita leerlo)."""
    return connection_service.beds24_adapter(session) if is_manual(session) else get_adapter(session)


@router.get("")
async def connection_status(session: AsyncSession = Depends(get_session)):
    conn = await connection_service.get(session)
    await session.commit()
    has_token = bool(secret_service.get_secret("beds24_refresh_token",
                                               current_account_id(session)))
    return {
        "mode": "manual" if is_manual(session) else "connected",
        "sandbox": settings.sandbox,
        "has_token": has_token or settings.sandbox,
        "selected_rooms": conn.selected_rooms,
        **connection_service.health(conn),
    }


class RedeemIn(BaseModel):
    code: str = Field(min_length=1, max_length=400)


@router.post("/beds24/redeem")
async def redeem(req: RedeemIn, session: AsyncSession = Depends(get_session),
                 ctx: RequestContext = Depends(require_ctx)):
    """Paso 2: canjea el código, prueba la conexión y devuelve las propiedades para elegir."""
    from app.channels.beds24_v2 import exchange_invite_code
    from app.channels.errors import AuthError, ChannelError

    await _require_owner(session, ctx)
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=422, detail="El código no puede estar vacío")
    if not settings.sandbox:  # en pruebas el canal es simulado: no se canjea nada real
        try:
            token = await exchange_invite_code(code, base_url=settings.beds24_v2_base_url)
        except AuthError:
            raise HTTPException(
                status_code=422,
                detail="Beds24 rechazó el código (¿vencido o ya usado?). Genera uno nuevo.",
            ) from None
        except ChannelError:
            raise HTTPException(status_code=503, detail=_UNAVAILABLE) from None
        await secret_service.set_secret(session, "beds24_refresh_token", token)
        await session.commit()
    adapter = _adapter(session)
    try:
        conn = await sync_service.test_connection(session, adapter)
    finally:
        await adapter.aclose()
    if conn.status.value != "connected":
        await session.commit()
        raise HTTPException(
            status_code=422,
            detail="El código se canjeó, pero Beds24 no deja leer las propiedades. Revisa que el "
                   "código tenga los permisos de lectura de properties, bookings e inventory.",
        )
    await connection_service.record_ok(session, conn.account_label)
    await session.commit()
    try:
        return {"ok": True, "account": conn.account_label, **(await _rooms(session))}
    except AuthError:
        raise HTTPException(status_code=422, detail="Beds24 rechazó el acceso al leer las propiedades.") from None
    except ChannelError:
        raise HTTPException(status_code=503, detail=_UNAVAILABLE) from None


@router.get("/beds24/rooms")
async def rooms(session: AsyncSession = Depends(get_session)):
    from app.channels.errors import AuthError, ChannelError

    try:
        return await _rooms(session)
    except AuthError:
        raise HTTPException(status_code=422, detail="Beds24 rechazó el acceso: reconecta con un código nuevo.") from None
    except ChannelError:
        raise HTTPException(status_code=503, detail=_UNAVAILABLE) from None


class SelectionIn(BaseModel):
    room_ids: list[str] | None = Field(default=None, max_length=500)  # None = todas


@router.put("/beds24/selection")
async def save_selection(req: SelectionIn, session: AsyncSession = Depends(get_session),
                         ctx: RequestContext = Depends(require_ctx)):
    """Paso 3: qué habitaciones sincroniza la cuenta. La importación (paso 4) es `/sync/import`."""
    await _require_owner(session, ctx)
    if req.room_ids is not None and not req.room_ids:
        raise HTTPException(status_code=422, detail="Elige al menos una habitación")
    await connection_service.set_selection(session, req.room_ids)
    await session.commit()
    return {"selected_rooms": req.room_ids}


class LinkIn(BaseModel):
    room_ids: list[str] = Field(min_length=1, max_length=500)
    links: dict[int, str] = Field(default_factory=dict, max_length=50)  # unidad manual → habitación


@router.put("/beds24/link")
async def link_manual(req: LinkIn, session: AsyncSession = Depends(get_session),
                      ctx: RequestContext = Depends(require_ctx)):
    """Entrega 2: de «sin conexión» a Beds24. Guarda la selección, asocia cada apartamento
    manual con su habitación y pasa la cuenta a conectada. Luego el asistente importa con
    `/sync/import`, que además quita las reservas duplicadas de iCal."""
    from app.channels.errors import AuthError, ChannelError

    await _require_owner(session, ctx)
    if not is_manual(session):
        raise HTTPException(status_code=409, detail="La cuenta ya está conectada a Beds24.")
    if any(r not in req.room_ids for r in req.links.values()):
        raise HTTPException(status_code=422, detail="Solo puedes asociar habitaciones que elegiste.")
    adapter = connection_service.beds24_adapter(session)
    try:
        props = await adapter.get_properties()
    except AuthError:
        raise HTTPException(status_code=422, detail="Beds24 rechazó el acceso: reconecta con un código nuevo.") from None
    except ChannelError:
        raise HTTPException(status_code=503, detail=_UNAVAILABLE) from None
    finally:
        await adapter.aclose()
    try:
        out = await connection_service.switch_from_manual(session, req.links, props)
    except connection_service.SwitchError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from None
    all_ids = {str(r.external_id) for p in props for r in p.rooms}
    await connection_service.set_selection(
        session, None if set(req.room_ids) >= all_ids else req.room_ids
    )
    await session.commit()
    return {**out, "mode": "connected"}
