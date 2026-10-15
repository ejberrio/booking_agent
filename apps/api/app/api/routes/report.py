"""Informe completo de la cuenta que se registró desde la página pública (feature 030)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, require_ctx
from app.db.session import get_session
from app.services import public_service

router = APIRouter()


@router.get("/mine")
async def my_report(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    data = await public_service.full_report(session, ctx.account_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Esta cuenta no viene de un informe")
    return data
