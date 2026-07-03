"""CRUD de notas del host sobre el calendario (feature 016). 100% local, sin CM."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import calendar_note_service
from app.services.calendar_note_service import CalendarNoteError

router = APIRouter()


class NoteCreateRequest(BaseModel):
    unit_type_id: int
    date_from: date
    date_to: date
    text: str


class NoteUpdateRequest(BaseModel):
    text: str | None = None
    date_from: date | None = None
    date_to: date | None = None


def _view(n) -> dict:
    return {
        "id": n.id,
        "unit_type_id": n.unit_type_id,
        "date_from": n.date_from.isoformat(),
        "date_to": n.date_to.isoformat(),
        "text": n.text,
    }


@router.get("")
async def list_notes(unit_type_id: int, session: AsyncSession = Depends(get_session)):
    notes = await calendar_note_service.list_notes(session, unit_type_id)
    return {"notes": [_view(n) for n in notes]}


@router.post("")
async def create_note(req: NoteCreateRequest, session: AsyncSession = Depends(get_session)):
    try:
        note = await calendar_note_service.create(
            session,
            unit_type_id=req.unit_type_id,
            date_from=req.date_from,
            date_to=req.date_to,
            text=req.text,
        )
        await session.commit()
        return _view(note)
    except CalendarNoteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{note_id}")
async def update_note(
    note_id: int, req: NoteUpdateRequest, session: AsyncSession = Depends(get_session)
):
    kwargs: dict = {}
    sent = req.model_fields_set
    if "text" in sent and req.text is not None:
        kwargs["text"] = req.text
    if "date_from" in sent and req.date_from is not None:
        kwargs["date_from"] = req.date_from
    if "date_to" in sent and req.date_to is not None:
        kwargs["date_to"] = req.date_to
    try:
        note = await calendar_note_service.update(session, note_id, **kwargs)
        await session.commit()
        return _view(note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CalendarNoteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{note_id}")
async def delete_note(note_id: int, session: AsyncSession = Depends(get_session)):
    try:
        await calendar_note_service.delete(session, note_id)
        await session.commit()
        return {"deleted": True}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
