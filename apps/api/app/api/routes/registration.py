"""Registro de huéspedes: TRA del MinCIT y SIRE (feature 046, #167). Panel del anfitrión.

Los datos personales nunca van a logs: solo se registra la reserva y el usuario.
"""

import logging
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.context import RequestContext, require_ctx
from app.db.session import get_session
from app.db.tenancy import current_account_id
from app.models.mixins import _now
from app.services import registration_service as svc
from app.services import secret_service
from app.services.usage_service import local_today

router = APIRouter()
log = logging.getLogger(__name__)


def _has_token(session: AsyncSession) -> bool:
    return settings.sandbox or bool(secret_service.get_secret(svc.TOKEN_SECRET, current_account_id(session)))


async def _settings_out(session: AsyncSession) -> dict:
    s = await svc.get_settings(session)
    has_token = _has_token(session)
    return {
        "rnt": s.rnt, "establishment_name": s.establishment_name,
        "accommodation": s.accommodation or {}, "sire_code": s.sire_code, "sire_city": s.sire_city,
        "authorized_at": s.authorized_at.isoformat() if s.authorized_at else None,
        "has_token": has_token, "sandbox": settings.sandbox,
        "missing": svc.missing_setup(s, has_token),
        "accommodations": list(svc.ACCOMMODATIONS),
    }


@router.get("/settings")
async def get_settings(session: AsyncSession = Depends(get_session)):
    out = await _settings_out(session)
    await session.commit()
    return out


class SettingsIn(BaseModel):
    rnt: str | None = Field(default=None, max_length=20)
    establishment_name: str | None = Field(default=None, max_length=120)
    accommodation: dict[str, str] | None = Field(default=None, max_length=200)
    sire_code: str | None = Field(default=None, max_length=20)
    sire_city: str | None = Field(default=None, max_length=20)
    authorize: bool | None = None


@router.put("/settings")
async def put_settings(req: SettingsIn, session: AsyncSession = Depends(get_session),
                       ctx: RequestContext = Depends(require_ctx)):
    s = await svc.get_settings(session)
    if req.rnt is not None:
        rnt = "".join(ch for ch in req.rnt if ch.isdigit())
        if req.rnt.strip() and not (3 <= len(rnt) <= 12):
            raise HTTPException(status_code=422, detail="El RNT debe tener solo números.")
        s.rnt = rnt or None
    if req.establishment_name is not None:
        s.establishment_name = " ".join(req.establishment_name.split()) or None
    if req.accommodation is not None:
        bad = [v for v in req.accommodation.values() if v not in svc.ACCOMMODATIONS]
        if bad:
            raise HTTPException(status_code=422, detail="Tipo de alojamiento no válido.")
        s.accommodation = {str(k): v for k, v in req.accommodation.items()}
    if req.sire_code is not None:
        s.sire_code = req.sire_code.strip() or None
    if req.sire_city is not None:
        s.sire_city = req.sire_city.strip() or None
    if req.authorize is not None:
        s.authorized_at = _now() if req.authorize else None
        s.authorized_by = ctx.user_id if req.authorize else None
    await session.flush()
    out = await _settings_out(session)
    await session.commit()
    return out


@router.get("")
async def overview(session: AsyncSession = Depends(get_session)):
    rows = await svc.overview(session, local_today())
    out = await _settings_out(session)
    await session.commit()
    return {"bookings": rows, "settings": out}


def _404(exc: LookupError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/{booking_id}/link")
async def link(booking_id: int, session: AsyncSession = Depends(get_session)):
    try:
        reg = await svc.ensure(session, booking_id)
    except LookupError as exc:
        raise _404(exc) from None
    await session.commit()
    return {"token": reg.token, "path": f"/checkin/{reg.token}"}


@router.get("/{booking_id}")
async def detail(booking_id: int, session: AsyncSession = Depends(get_session)):
    try:
        out = await svc.detail(session, booking_id, local_today())
    except LookupError as exc:
        raise _404(exc) from None
    await session.commit()
    return out


class GuestsIn(BaseModel):
    data: dict
    cost_cop: str | None = Field(default=None, max_length=20)


@router.put("/{booking_id}")
async def save(booking_id: int, req: GuestsIn, session: AsyncSession = Depends(get_session)):
    """El anfitrión llena o corrige los datos (antes de enviar la TRA)."""
    try:
        reg = await svc.ensure(session, booking_id)
        v = await svc.save(session, reg, req.data, by=reg.filled_by or "host", today=local_today())
    except LookupError as exc:
        raise _404(exc) from None
    except svc.RegistrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    if v.errors:
        raise HTTPException(status_code=422, detail={"message": "Revisa los campos marcados.", "fields": v.errors})
    if req.cost_cop is not None:
        raw = req.cost_cop.replace(".", "").replace(",", "").strip()
        try:
            reg.cost_cop = Decimal(raw) if raw else None
        except InvalidOperation:
            raise HTTPException(status_code=422, detail="El costo debe ser un número en pesos.") from None
    await session.commit()
    return await detail(booking_id, session)


@router.post("/{booking_id}/tra")
async def send_tra(booking_id: int, session: AsyncSession = Depends(get_session),
                   ctx: RequestContext = Depends(require_ctx)):
    s = await svc.get_settings(session)
    missing = svc.missing_setup(s, _has_token(session))
    if missing:
        raise HTTPException(status_code=409, detail={"message": "Completa la configuración del registro en Ajustes.",
                                                     "missing": missing})
    token = secret_service.get_secret(svc.TOKEN_SECRET, current_account_id(session)) or ""
    client = svc.tra_client(token)
    try:
        reg = await svc.send_tra(session, booking_id, client)
    except LookupError as exc:
        raise _404(exc) from None
    except svc.RegistrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    finally:
        await client.aclose()
    await session.commit()
    log.info("TRA: reserva=%s usuario=%s estado=%s", booking_id, ctx.user_id, reg.status)  # sin datos
    return await detail(booking_id, session)
