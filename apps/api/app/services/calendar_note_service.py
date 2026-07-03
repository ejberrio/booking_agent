"""Notas del host sobre días/rangos del calendario (feature 016).

Memoria local del host (típico: el porqué de un bloqueo). Este servicio nunca
llama al Channel Manager. Solapes permitidos sin límite; borrado real.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarNote

_MAX_LEN = 500
_UNSET = object()


class CalendarNoteError(ValueError):
    """Datos inválidos para una nota."""


def _validate(text: str, date_from: date, date_to: date) -> str:
    clean = (text or "").strip()
    if not clean:
        raise CalendarNoteError("La nota no puede estar vacía")
    if len(clean) > _MAX_LEN:
        raise CalendarNoteError(f"La nota supera el máximo de {_MAX_LEN} caracteres")
    if date_from > date_to:
        raise CalendarNoteError("La fecha de fin no puede ser anterior a la de inicio")
    return clean


async def list_notes(session: AsyncSession, unit_type_id: int) -> list[CalendarNote]:
    stmt = (
        select(CalendarNote)
        .where(CalendarNote.unit_type_id == unit_type_id)
        .order_by(CalendarNote.date_from, CalendarNote.id)
    )
    return list((await session.execute(stmt)).scalars())


async def create(
    session: AsyncSession, *, unit_type_id: int, date_from: date, date_to: date, text: str
) -> CalendarNote:
    clean = _validate(text, date_from, date_to)
    note = CalendarNote(
        unit_type_id=unit_type_id, date_from=date_from, date_to=date_to, text=clean
    )
    session.add(note)
    await session.flush()
    return note


async def update(
    session: AsyncSession,
    note_id: int,
    *,
    text: str | object = _UNSET,
    date_from: date | object = _UNSET,
    date_to: date | object = _UNSET,
) -> CalendarNote:
    note = await session.get(CalendarNote, note_id)
    if note is None:
        raise LookupError(f"No existe la nota {note_id}")
    new_text = note.text if text is _UNSET else text
    new_from = note.date_from if date_from is _UNSET else date_from
    new_to = note.date_to if date_to is _UNSET else date_to
    note.text = _validate(new_text, new_from, new_to)
    note.date_from = new_from
    note.date_to = new_to
    await session.flush()
    return note


async def delete(session: AsyncSession, note_id: int) -> None:
    note = await session.get(CalendarNote, note_id)
    if note is None:
        raise LookupError(f"No existe la nota {note_id}")
    await session.delete(note)
    await session.flush()
