"""Panel del administrador de plataforma (feature 026, entrega 3). Solo `is_platform_admin`."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, require_platform_admin
from app.db.session import get_session
from app.services import admin_service, invite_service

router = APIRouter(dependencies=[Depends(require_platform_admin)])


@router.get("/invites")
async def list_invites(session: AsyncSession = Depends(get_session)):
    return await invite_service.list_invites(session)


class InviteCreate(BaseModel):
    note: str | None = Field(default=None, max_length=200)
    days: int = Field(default=30, ge=1, le=180)


@router.post("/invites")
async def create_invite(
    req: InviteCreate,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_platform_admin),
):
    inv, code = await invite_service.create(
        session, note=req.note, days=req.days, by_user_id=ctx.user_id
    )
    await session.commit()
    # ÚNICA vez que el código completo sale de la API.
    return {"id": inv.id, "code": code, "note": inv.note, "expires_at": inv.expires_at.isoformat()}


@router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: int, session: AsyncSession = Depends(get_session)):
    try:
        await invite_service.revoke(session, invite_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    await session.commit()
    return {"revoked": True}


@router.get("/accounts")
async def list_accounts():
    return await admin_service.list_accounts()


@router.post("/accounts/{account_id}/disable")
async def disable_account(account_id: int, ctx: RequestContext = Depends(require_platform_admin)):
    try:
        return await admin_service.set_status(account_id, enabled=False, by_account_id=ctx.account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/accounts/{account_id}/enable")
async def enable_account(account_id: int, ctx: RequestContext = Depends(require_platform_admin)):
    try:
        return await admin_service.set_status(account_id, enabled=True, by_account_id=ctx.account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/settings")
async def get_settings(session: AsyncSession = Depends(get_session)):
    return {"registration_open": await invite_service.registration_open(session)}


class SettingsPatch(BaseModel):
    registration_open: bool


@router.patch("/settings")
async def patch_settings(req: SettingsPatch, session: AsyncSession = Depends(get_session)):
    await invite_service.set_registration_open(session, req.registration_open)
    await session.commit()
    return {"registration_open": req.registration_open}


# --------- uso de IA (feature 027) ---------


@router.get("/usage")
async def ai_usage(month: str | None = None):
    from datetime import date

    from app.services.usage_service import local_today

    try:
        day = date.fromisoformat(f"{month}-01") if month else local_today()
    except ValueError:
        raise HTTPException(status_code=422, detail="Mes inválido (AAAA-MM)") from None
    return await admin_service.usage(day)


class LimitsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    chat_limit_month: int | None = Field(default=None, ge=0, le=100_000)
    search_limit_day: int | None = Field(default=None, ge=0, le=1_000)


@router.patch("/accounts/{account_id}/limits")
async def set_limits(account_id: int, req: LimitsRequest):
    fields = {k: getattr(req, k) for k in req.model_fields_set}
    try:
        return await admin_service.set_limits(account_id, **fields)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
