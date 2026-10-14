"""Cuenta y unidades de la sesión (feature 026).

`GET /units` reemplaza el "unidad 1" fijo de la web: cada cuenta ve solo las suyas
(lista vacía → la web muestra cómo conectar su channel manager).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import has_credentials
from app.core.context import RequestContext, require_ctx
from app.db.session import get_session
from app.models.account import Account
from app.models.property import Property, UnitType

router = APIRouter()


@router.get("/units")
async def list_units(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(UnitType, Property)
            .join(Property, UnitType.property_id == Property.id)
            .order_by(Property.id, UnitType.id)
        )
    ).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "property_id": p.id,
            "property_name": p.name,
            "city": p.city,
            "currency": p.currency,
        }
        for u, p in rows
    ]


async def _account(session: AsyncSession, ctx: RequestContext) -> Account:
    acc = await session.get(Account, ctx.account_id)
    if acc is None:  # pragma: no cover — la sesión ya validó la cuenta
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return acc


def _out(acc: Account, session: AsyncSession) -> dict:
    return {
        "id": acc.id,
        "name": acc.name,
        "status": acc.status.value,
        "connected": has_credentials(session),
    }


@router.get("/account")
async def get_account(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    return _out(await _account(session, ctx), session)


class AccountPatch(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.patch("/account")
async def patch_account(
    req: AccountPatch,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_ctx),
):
    acc = await _account(session, ctx)
    acc.name = req.name.strip()
    await session.commit()
    return _out(acc, session)


# --------- derechos del titular (feature 028) ---------


async def _owner(session: AsyncSession, ctx: RequestContext):
    from app.models.auth import AppUser

    if ctx.user_id is None:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    user = await session.get(AppUser, ctx.user_id)
    if user is None:  # pragma: no cover
        raise HTTPException(status_code=401, detail="Sesión no válida")
    return user, await _account(session, ctx)


@router.get("/account/export")
async def export_account(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    """Copia de todos los datos de la cuenta (derecho de acceso), sin credenciales."""
    from app.services import privacy_service

    user, acc = await _owner(session, ctx)
    return await privacy_service.export_account(session, user, acc)


@router.post("/account/delete-code", status_code=202)
async def account_delete_code(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    from app.services import auth_service

    user, _ = await _owner(session, ctx)
    if user.password_hash:
        return {"sent": False, "reason": "use_password"}
    return {"sent": await auth_service.send_delete_code(session, user)}


class DeleteAccountRequest(BaseModel):
    account_name: str = Field(max_length=120)
    password: str | None = Field(default=None, max_length=256)
    code: str | None = Field(default=None, max_length=12)


def _err(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "code": code})


@router.post("/account/delete")
async def delete_account(
    req: DeleteAccountRequest,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_ctx),
):
    """Borra la cuenta y todos sus datos (derecho de supresión). Irreversible."""
    from app.models.account import FIRST_ACCOUNT_ID
    from app.services import auth_service, privacy_service
    from app.email import templates

    user, acc = await _owner(session, ctx)
    if acc.id == FIRST_ACCOUNT_ID:
        return _err(409, "protected", "La cuenta principal no se puede borrar desde aquí")
    if req.account_name.strip() != acc.name.strip():
        return _err(400, "name_mismatch", "El nombre de la cuenta no coincide")
    if not await auth_service.confirm_identity(
        session, user, password=req.password, code=req.code
    ):
        return _err(400, "invalid_credentials", "No pudimos confirmar que eres tú")
    email, lang, name, acc_id = user.email, user.language, user.name, acc.id
    await session.rollback()  # suelta la sesión de la cuenta antes del borrado
    await privacy_service.delete_account(acc_id)
    sender = auth_service.get_email_sender()
    if sender is not None:
        try:
            await sender.send(templates.account_deleted(email, lang, name))
        except Exception:  # noqa: BLE001 — el borrado ya ocurrió; el correo es cortesía
            pass
    return {"status": "deleted"}
