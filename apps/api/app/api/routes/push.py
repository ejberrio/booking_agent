"""Avisos al celular (feature 025): registro de teléfonos, preferencias y prueba."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import push_service

router = APIRouter()


class DeviceRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    platform: Literal["android", "ios"] = "android"
    model: str | None = Field(default=None, max_length=120)
    app_version: str | None = Field(default=None, max_length=32)


class DevicePatch(BaseModel):
    notify_bookings: bool | None = None
    notify_suggestions: bool | None = None


def _view(d) -> dict:
    # Nunca se devuelve el token del teléfono.
    return {
        "id": d.id,
        "platform": d.platform,
        "model": d.model,
        "app_version": d.app_version,
        "notify_bookings": d.notify_bookings,
        "notify_suggestions": d.notify_suggestions,
        "enabled": d.enabled,
        "last_seen_at": d.last_seen_at,
        "last_error": d.last_error,
    }


@router.post("/devices")
async def register(req: DeviceRequest, session: AsyncSession = Depends(get_session)):
    dev = await push_service.register_device(
        session, token=req.token, platform=req.platform, model=req.model, app_version=req.app_version
    )
    await session.commit()
    return _view(dev)


@router.get("/devices")
async def devices(session: AsyncSession = Depends(get_session)):
    return [_view(d) for d in await push_service.list_devices(session)]


@router.patch("/devices/{device_id}")
async def patch_device(device_id: int, req: DevicePatch, session: AsyncSession = Depends(get_session)):
    try:
        dev = await push_service.update_device(
            session,
            device_id,
            notify_bookings=req.notify_bookings,
            notify_suggestions=req.notify_suggestions,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _view(dev)


@router.delete("/devices/{device_id}")
async def remove_device(device_id: int, session: AsyncSession = Depends(get_session)):
    try:
        await push_service.delete_device(session, device_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return {"deleted": True}


@router.post("/test")
async def test(session: AsyncSession = Depends(get_session)):
    result = await push_service.send_test(session)
    await session.commit()
    return result


@router.get("/status")
async def status(session: AsyncSession = Depends(get_session)):
    devs = await push_service.list_devices(session)
    return {"configured": push_service.configured(), "devices": sum(1 for d in devs if d.enabled)}
