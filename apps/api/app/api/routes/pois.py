"""POIs y configuración del scan (feature 018). Datos locales, cero llamadas al CM."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.market import PointOfInterest
from app.services.intelligence_service import effective_zone, get_or_create_scan_config

router = APIRouter()


class PoiCreateRequest(BaseModel):
    name: str
    note: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_active: bool = True


class PoiUpdateRequest(BaseModel):
    name: str | None = None
    note: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_active: bool | None = None


class ScanConfigRequest(BaseModel):
    zone: str | None = None
    queries_per_scan: int | None = None
    event_kinds: str | None = None


def _poi_view(p: PointOfInterest) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "note": p.note,
        "date_from": p.date_from.isoformat() if p.date_from else None,
        "date_to": p.date_to.isoformat() if p.date_to else None,
        "is_active": p.is_active,
    }


def _validate_poi(name: str, date_from, date_to) -> str:
    clean = (name or "").strip()
    if not clean:
        raise HTTPException(status_code=422, detail="El nombre del sitio es obligatorio")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422, detail="La fecha de fin no puede ser anterior a la de inicio"
        )
    return clean


@router.get("/pois")
async def list_pois(session: AsyncSession = Depends(get_session)):
    rows = (
        (await session.execute(select(PointOfInterest).order_by(PointOfInterest.id)))
        .scalars()
        .all()
    )
    return {"pois": [_poi_view(p) for p in rows]}


@router.post("/pois")
async def create_poi(req: PoiCreateRequest, session: AsyncSession = Depends(get_session)):
    name = _validate_poi(req.name, req.date_from, req.date_to)
    poi = PointOfInterest(
        name=name,
        note=req.note,
        date_from=req.date_from,
        date_to=req.date_to,
        is_active=req.is_active,
    )
    session.add(poi)
    await session.commit()
    return _poi_view(poi)


@router.patch("/pois/{poi_id}")
async def update_poi(
    poi_id: int, req: PoiUpdateRequest, session: AsyncSession = Depends(get_session)
):
    poi = await session.get(PointOfInterest, poi_id)
    if poi is None:
        raise HTTPException(status_code=404, detail="No existe el sitio")
    sent = req.model_fields_set
    new_name = req.name if "name" in sent and req.name is not None else poi.name
    new_from = req.date_from if "date_from" in sent else poi.date_from
    new_to = req.date_to if "date_to" in sent else poi.date_to
    poi.name = _validate_poi(new_name, new_from, new_to)
    poi.date_from = new_from
    poi.date_to = new_to
    if "note" in sent:
        poi.note = req.note
    if "is_active" in sent and req.is_active is not None:
        poi.is_active = req.is_active
    await session.commit()
    return _poi_view(poi)


@router.delete("/pois/{poi_id}")
async def delete_poi(poi_id: int, session: AsyncSession = Depends(get_session)):
    poi = await session.get(PointOfInterest, poi_id)
    if poi is None:
        raise HTTPException(status_code=404, detail="No existe el sitio")
    await session.delete(poi)
    await session.commit()
    return {"deleted": True}


# --------- configuración del scan (fila única, autocreada) ---------


def _config_view(cfg, zone: str) -> dict:
    return {
        "zone": cfg.zone,
        "effective_zone": zone,
        "queries_per_scan": cfg.queries_per_scan,
        "event_kinds": cfg.event_kinds,
    }


@router.get("/scan-config")
async def get_scan_config(session: AsyncSession = Depends(get_session)):
    cfg = await get_or_create_scan_config(session)
    await session.commit()
    return _config_view(cfg, await effective_zone(session, cfg))


@router.put("/scan-config")
async def update_scan_config(
    req: ScanConfigRequest, session: AsyncSession = Depends(get_session)
):
    cfg = await get_or_create_scan_config(session)
    sent = req.model_fields_set
    if "queries_per_scan" in sent and req.queries_per_scan is not None:
        if not (1 <= req.queries_per_scan <= 30):
            raise HTTPException(
                status_code=422, detail="Las consultas por corrida deben estar entre 1 y 30"
            )
        cfg.queries_per_scan = req.queries_per_scan
    if "zone" in sent:
        cfg.zone = (req.zone or "").strip() or None
    if "event_kinds" in sent:
        cfg.event_kinds = (req.event_kinds or "").strip() or None
    await session.commit()
    return _config_view(cfg, await effective_zone(session, cfg))
