"""Cuenta y unidades de la sesión (feature 026).

`GET /units` reemplaza el "unidad 1" fijo de la web: cada cuenta ve solo las suyas
(lista vacía → la web muestra cómo conectar su channel manager).
"""

from fastapi import APIRouter, Depends, HTTPException
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
