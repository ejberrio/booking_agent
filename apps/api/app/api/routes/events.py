"""Eventos del área de la propiedad y reporte de eventos faltantes (feature 035)."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import event_report_service as svc

router = APIRouter()


@router.get("")
async def list_events(
    date_from: date | None = None, date_to: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    today = date.today()
    df = date_from or today
    dt = date_to or df + timedelta(days=90)
    return await svc.list_events(session, df, min(dt, df + timedelta(days=400)))


class ReportIn(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    start_date: date
    end_date: date | None = None
    venue: str | None = Field(default=None, max_length=200)


@router.post("/report")
async def report_event(req: ReportIn, session: AsyncSession = Depends(get_session)):
    try:
        res = await svc.report_metered(session, name=req.name, start_date=req.start_date,
                                       end_date=req.end_date, venue=req.venue)
    except svc.ReportError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    return {"status": res.status, "event": res.event, "message": res.message,
            "remaining_today": max(0, svc.REPORTS_PER_DAY - await svc.reports_today(session))}
