from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import get_adapter  # noqa: F401  -- re-exportado (feature 026)
from app.db.session import get_session
from app.db.cross_account import PropertyOwnedElsewhere
from app.services import push_service, sync_service

router = APIRouter()


class ImportRequest(BaseModel):
    days: int = 730


class PublishRequest(BaseModel):
    unit_type_id: int
    date_from: date
    date_to: date
    price: Decimal


@router.post("/test")
async def test_connection(session: AsyncSession = Depends(get_session)):
    adapter = get_adapter(session)
    try:
        conn = await sync_service.test_connection(session, adapter)
        await session.commit()
        return {"status": conn.status.value, "account": conn.account_label}
    finally:
        await adapter.aclose()


@router.post("/import")
async def import_remote(req: ImportRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter(session)
    try:
        today = date.today()
        events: list = []
        try:
            run = await sync_service.import_remote(
                session, adapter, today, today + timedelta(days=req.days), events=events
            )
        except PropertyOwnedElsewhere as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        await push_service.notify_booking_events(session, events)  # feature 025
        await session.commit()
        return {
            "run_id": run.id,
            "status": run.status.value,
            "created": run.created_count,
            "updated": run.updated_count,
            "issues": run.issue_count,
        }
    finally:
        await adapter.aclose()


@router.post("/publish")
async def publish(req: PublishRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter(session)
    try:
        run = await sync_service.publish_price(
            session,
            adapter,
            unit_type_id=req.unit_type_id,
            date_from=req.date_from,
            date_to=req.date_to,
            price=req.price,
        )
        await session.commit()
        return {"run_id": run.id, "status": run.status.value, "issues": run.issue_count}
    finally:
        await adapter.aclose()


@router.get("/issues")
async def list_issues(session: AsyncSession = Depends(get_session)):
    issues = await sync_service.list_open_issues(session)
    return [
        {"id": i.id, "kind": i.kind.value, "entity": i.entity_ref, "detail": i.detail}
        for i in issues
    ]
