"""Rutas SIN sesión de la página pública (feature 030).

Solo las llama el servidor web (`/api/public/*`), que pasa la IP del visitante en
`x-client-ip`; la API no está expuesta a internet. Solo datos públicos (eventos por ciudad).
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain import municipalities
from app.services import public_service
from app.services.public_service import PublicError, ReportInput

router = APIRouter()


def _ip(request: Request) -> str | None:
    return request.headers.get("x-client-ip") or (request.client.host if request.client else None)


def _error(exc: PublicError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "detail": exc.detail})


def search_provider():
    """Búsqueda web para municipios nuevos; None si no está configurada (se sirve la caché)."""
    from app.services.secret_service import get_secret

    if not get_secret("search_api_key"):
        return None
    from app.search.tavily import TavilyProvider

    return TavilyProvider()


def llm_provider():
    from app.llm.client import default_llm

    return default_llm()


@router.get("/municipalities")
async def list_municipalities(q: str = ""):
    return [m.as_dict() for m in municipalities.search(q[:60])]


class ReportRequest(BaseModel):
    municipality_code: str = Field(max_length=5)
    weekday_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    weekend_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="COP", max_length=3)
    unit_kind: str | None = Field(default=None, max_length=20)
    language: str = Field(default="es", max_length=2)


@router.post("/report")
async def report(req: ReportRequest, request: Request, session: AsyncSession = Depends(get_session)):
    search = search_provider()
    try:
        return await public_service.create_report(
            session,
            ReportInput(**req.model_dump()),
            ip=_ip(request),
            search=search,
            llm=llm_provider() if search is not None else None,
        )
    except PublicError as exc:
        return _error(exc)
    finally:
        if search is not None and hasattr(search, "aclose"):
            await search.aclose()


class WaitlistRequest(BaseModel):
    email: str = Field(max_length=254)
    consent: bool = False
    language: str = Field(default="es", max_length=2)
    municipality_code: str | None = Field(default=None, max_length=5)


@router.post("/waitlist")
async def waitlist(
    req: WaitlistRequest, request: Request, session: AsyncSession = Depends(get_session)
):
    try:
        await public_service.join_waitlist(
            session, email=req.email, consent=req.consent, language=req.language,
            municipality_code=req.municipality_code, ip=_ip(request),
        )
    except PublicError as exc:
        return _error(exc)
    return {"ok": True}


@router.post("/visit")
async def visit(session: AsyncSession = Depends(get_session)):
    await public_service.bump(session, public_service.VISIT)
    await session.commit()
    return {"ok": True}


class UnsubscribeRequest(BaseModel):
    u: int
    t: str = Field(max_length=64)


@router.post("/unsubscribe")
async def unsubscribe(req: UnsubscribeRequest, session: AsyncSession = Depends(get_session)):
    """Apaga el resumen semanal desde el enlace firmado del correo (sin sesión)."""
    from app.services import digest_service

    ok = await digest_service.unsubscribe(session, req.u, req.t)
    if not ok:
        return JSONResponse(status_code=400, content={"code": "invalid_link", "detail": "Enlace no válido"})
    return {"ok": True}


# --------- registro de huéspedes (feature 046): formulario del enlace /checkin/{token} ---------

_CLOSED = {"code": "not_found", "detail": "Este enlace no existe o ya venció."}
CHECKIN_DAILY_LIMIT = 30  # envíos por visitante y día (evita abuso del enlace)


async def _registration(session: AsyncSession, token: str):
    """(registro, reserva) del enlace, o None. Fija la cuenta en la sesión."""
    from app.db.cross_account import registration_account
    from app.db.tenancy import set_tenant
    from app.models.booking import Booking
    from app.services import registration_service as reg_svc

    if not (20 <= len(token) <= 64):
        return None
    account_id = await registration_account(session, token)
    if account_id is None:
        return None
    set_tenant(session, account_id)
    from sqlalchemy import select

    from app.models.registration import GuestRegistration

    reg = (await session.execute(select(GuestRegistration).where(GuestRegistration.token == token))).scalar_one_or_none()
    if reg is None:
        return None
    b = await session.get(Booking, reg.booking_id)
    from app.services.usage_service import local_today

    if b is None or not reg_svc.link_open(b, reg, local_today()):
        return None
    return reg, b


@router.get("/checkin/{token}")
async def checkin_info(token: str, session: AsyncSession = Depends(get_session)):
    """Solo lo necesario para el formulario: alojamiento, ciudad y fechas (sin nombre)."""
    from app.models.property import Property, UnitType
    from app.services import registration_service as reg_svc

    found = await _registration(session, token)
    if found is None:
        return JSONResponse(status_code=404, content=_CLOSED)
    reg, b = found
    unit = await session.get(UnitType, b.unit_type_id)
    prop = await session.get(Property, unit.property_id) if unit else None
    return {
        "unit": unit.name if unit else None, "city": prop.city if prop else None,
        "check_in": b.check_in.isoformat(), "check_out": b.check_out.isoformat(),
        "submitted": reg.submitted_at is not None,
        "max_companions": reg_svc.MAX_COMPANIONS,
        "motives": list(reg_svc.MOTIVES),
    }


class CheckinRequest(BaseModel):
    data: dict
    consent: bool = False


@router.post("/checkin/{token}")
async def checkin_submit(token: str, req: CheckinRequest, request: Request,
                         session: AsyncSession = Depends(get_session)):
    """El huésped envía (o corrige) sus datos. Nunca devuelve los datos guardados."""
    from app.services import registration_service as reg_svc
    from app.services.usage_service import local_today

    try:
        await public_service._take(session, public_service.visitor_id(_ip(request)), "checkin",
                                   CHECKIN_DAILY_LIMIT)
    except PublicError as exc:
        return _error(exc)
    found = await _registration(session, token)
    if found is None:
        await session.commit()  # el intento cuenta para el límite
        return JSONResponse(status_code=404, content=_CLOSED)
    if not req.consent:
        return JSONResponse(status_code=422, content={"code": "consent", "detail": "Debes aceptar el aviso de privacidad."})
    reg, _ = found
    try:
        v = await reg_svc.save(session, reg, req.data, by="guest", today=local_today())
    except reg_svc.RegistrationError as exc:
        return JSONResponse(status_code=409, content={"code": "locked", "detail": str(exc)})
    if v.errors:
        await session.commit()
        return JSONResponse(status_code=422, content={"code": "invalid", "detail": "Revisa los campos marcados.",
                                                      "fields": v.errors})
    await session.commit()
    await reg_svc.notify_submitted(session, reg, found[1])
    return {"ok": True}
