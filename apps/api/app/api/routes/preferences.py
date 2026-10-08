"""Preferencias del host (feature 021): idioma de la app para todos sus dispositivos."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.preference import LANGUAGES, AppPreference

router = APIRouter()


class PreferencesBody(BaseModel):
    language: str


async def _get_or_create(session: AsyncSession) -> AppPreference:
    pref = (await session.execute(select(AppPreference).order_by(AppPreference.id))).scalars().first()
    if pref is None:
        pref = AppPreference(language="es")
        session.add(pref)
        await session.flush()
    return pref


@router.get("")
async def get_preferences(session: AsyncSession = Depends(get_session)):
    pref = await _get_or_create(session)
    await session.commit()
    return {"language": pref.language}


@router.put("")
async def put_preferences(body: PreferencesBody, session: AsyncSession = Depends(get_session)):
    if body.language not in LANGUAGES:
        raise HTTPException(status_code=422, detail="Idioma no soportado")
    pref = await _get_or_create(session)
    pref.language = body.language
    await session.commit()
    return {"language": pref.language}
