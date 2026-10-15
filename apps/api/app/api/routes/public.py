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
