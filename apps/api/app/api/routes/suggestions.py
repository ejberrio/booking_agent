from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.models.enums import SuggestionStatus, SyncIssueKind
from app.models.sync import SyncIssue
from app.services import intelligence_service, pricing_service
from app.services.intelligence_service import SuggestionPublishError, SuggestionStateError

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


async def _with_current_price(session: AsyncSession, s, today: date) -> dict:
    """Serializa con el precio base vigente del primer día no pasado del rango (FR-004)."""
    data = _serialize(s)
    current = None
    if s.unit_type_id is not None:
        day = min(max(s.date_from, today), s.date_to)
        price = await pricing_service.get_price(session, s.unit_type_id, day)
        current = str(price) if price is not None else None
    data["current_price"] = current
    return data


@router.get("")
async def list_suggestions(
    status: str | None = None,
    pending: bool = False,
    session: AsyncSession = Depends(get_session),
):
    if pending:
        items = await intelligence_service.list_suggestions(
            session, statuses=[SuggestionStatus.proposed, SuggestionStatus.approved]
        )
    else:
        st = SuggestionStatus(status) if status else None
        items = await intelligence_service.list_suggestions(session, status=st)
    today = date.today()
    return [await _with_current_price(session, s, today) for s in items]


@router.post("/{suggestion_id}/reject")
async def reject(suggestion_id: int, session: AsyncSession = Depends(get_session)):
    try:
        s = await intelligence_service.reject(session, suggestion_id)
        await session.commit()
        return _serialize(s)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{suggestion_id}/apply")
async def apply(suggestion_id: int, session: AsyncSession = Depends(get_session)):
    """Acción única "Aprobar y aplicar" (feature 014): aprueba+aplica+publica+audita."""
    adapter = get_adapter()
    try:
        sug, applied_from, issues = await intelligence_service.apply_suggestion(
            session, adapter, suggestion_id
        )
        await session.commit()
        data = await _with_current_price(session, sug, date.today())
        data["applied_from"] = applied_from.isoformat()
        data["publish_issues"] = issues
        return data
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SuggestionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SuggestionPublishError as exc:
        # Nada queda aplicado: se descarta la transacción y solo persiste la incidencia.
        await session.rollback()
        session.add(
            SyncIssue(
                kind=SyncIssueKind.comm_error,
                entity_ref=f"suggestion:{suggestion_id}",
                detail=str(exc),
            )
        )
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await adapter.aclose()
