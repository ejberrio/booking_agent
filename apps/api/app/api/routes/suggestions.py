from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.models.enums import SuggestionStatus
from app.services import intelligence_service

router = APIRouter()


def _serialize(s) -> dict:
    return {
        "id": s.id,
        "unit_type_id": s.unit_type_id,
        "date_from": s.date_from.isoformat(),
        "date_to": s.date_to.isoformat(),
        "suggested_price": str(s.suggested_price),
        "rationale": s.rationale,
        "confidence": str(s.confidence) if s.confidence is not None else None,
        "status": s.status.value,
    }


@router.get("")
async def list_suggestions(status: str | None = None, session: AsyncSession = Depends(get_session)):
    st = SuggestionStatus(status) if status else None
    items = await intelligence_service.list_suggestions(session, status=st)
    return [_serialize(s) for s in items]


@router.post("/{suggestion_id}/approve")
async def approve(suggestion_id: int, session: AsyncSession = Depends(get_session)):
    try:
        s = await intelligence_service.approve(session, suggestion_id)
        await session.commit()
        return _serialize(s)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{suggestion_id}/reject")
async def reject(suggestion_id: int, session: AsyncSession = Depends(get_session)):
    try:
        s = await intelligence_service.reject(session, suggestion_id)
        await session.commit()
        return _serialize(s)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{suggestion_id}/apply")
async def apply(suggestion_id: int, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        s = await intelligence_service.apply_suggestion(session, adapter, suggestion_id)
        await session.commit()
        return _serialize(s)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        await adapter.aclose()
