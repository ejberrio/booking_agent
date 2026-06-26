from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.beds24 import Beds24Adapter
from app.channels.beds24_v2 import Beds24V2Adapter
from app.core.config import settings
from app.db.session import get_session
from app.services import sync_service

router = APIRouter()


def get_adapter():
    # V2 (token) es obligatoria para escribir precios; V1 solo lee. Se elige por config.
    if settings.beds24_api_version == "v2":
        return Beds24V2Adapter(
            refresh_token=settings.beds24_refresh_token,
            prop_id=settings.beds24_prop_id,
            room_id=settings.beds24_room_id,
            base_url=settings.beds24_v2_base_url,
        )
    return Beds24Adapter(
        api_key=settings.beds24_api_key,
        prop_key=settings.beds24_prop_key,
        prop_id=settings.beds24_prop_id,
        room_id=settings.beds24_room_id,
        base_url=settings.beds24_base_url,
    )


class ImportRequest(BaseModel):
    days: int = 365


class PublishRequest(BaseModel):
    unit_type_id: int
    date_from: date
    date_to: date
    price: Decimal


@router.post("/test")
async def test_connection(session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        conn = await sync_service.test_connection(session, adapter)
        await session.commit()
        return {"status": conn.status.value, "account": conn.account_label}
    finally:
        await adapter.aclose()


@router.post("/import")
async def import_remote(req: ImportRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        today = date.today()
        run = await sync_service.import_remote(session, adapter, today, today + timedelta(days=req.days))
        await session.commit()
        return {
            "run_id": run.id,
            "status": run.status.value,
            "created": run.created_count,
            "issues": run.issue_count,
        }
    finally:
        await adapter.aclose()


@router.post("/publish")
async def publish(req: PublishRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
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
