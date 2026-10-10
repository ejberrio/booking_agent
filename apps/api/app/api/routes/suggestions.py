from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.models.enums import SuggestionStatus, SyncIssueKind
from app.models.sync import SyncIssue
from app.domain.suggestion_blocks import BlockInput, build_blocks
from app.services import intelligence_service, pricing_service, suggestion_batch
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


# --------- sugerencias accionables (feature 019) ---------
# Declaradas ANTES de /{suggestion_id}/... para que "batch" no se lea como un id.

_STALE = "La vista previa cambió (precios, reservas o sugerencias); revísala de nuevo."


def _money(v) -> str | None:
    return str(v) if v is not None else None


def _night(n) -> dict:
    return {
        "date": n.date.isoformat(),
        "suggestion_id": n.suggestion_id,
        "current_price": _money(n.current_price),
        "suggested_price": _money(n.suggested_price),
    }


@router.get("/blocks")
async def list_blocks(unit_type_id: int | None = None, session: AsyncSession = Depends(get_session)):
    """Pendientes reducidas a noches vendibles y agrupadas por evento/periodo."""
    views = await suggestion_batch.pending_views(session, unit_type_id=unit_type_id)
    by_id = {v.suggestion.id: v for v in views}
    blocks = build_blocks(
        [
            BlockInput(
                suggestion_id=v.suggestion.id,
                nights=v.nights,
                factors=(v.suggestion.rationale or {}).get("factors") or [],
            )
            for v in views
        ]
    )
    return {
        "blocks": [
            {
                "key": b.key,
                "kind": b.kind,
                "title": b.title,
                "date_from": b.date_from.isoformat(),
                "date_to": b.date_to.isoformat(),
                "direction": b.direction,
                "suggestion_ids": b.suggestion_ids,
                "nights": [_night(n) for n in b.nights],
                "suggestions": [
                    {
                        **_serialize(by_id[sid].suggestion),
                        "total_nights": by_id[sid].total_nights,
                        "sellable_count": len(by_id[sid].nights),
                        "occupied_count": by_id[sid].occupied_count,
                    }
                    for sid in b.suggestion_ids
                ],
            }
            for b in blocks
        ],
        "hidden_occupied": sum(v.occupied_count for v in views),
    }


class BatchRequest(BaseModel):
    suggestion_ids: list[int]


class BatchApplyRequest(BatchRequest):
    fingerprint: str


def _require_ids(ids: list[int]) -> None:
    if not ids:
        raise HTTPException(status_code=422, detail="Selecciona al menos una sugerencia")


@router.post("/batch/preview")
async def batch_preview(req: BatchRequest, session: AsyncSession = Depends(get_session)):
    _require_ids(req.suggestion_ids)
    p = await suggestion_batch.preview_batch(session, req.suggestion_ids)
    return {
        "suggestion_ids": p.suggestion_ids,
        "items": [
            {
                "date": i.date.isoformat(),
                "suggestion_id": i.suggestion_id,
                "old_price": _money(i.old_price),
                "new_price": _money(i.new_price),
                "valid": i.valid,
                "reason": i.reason,
                # feature 022
                "mode": i.mode,
                "promo_price": _money(i.promo_price),
                "promo_pct": _money(i.promo_pct),
                "clipped": i.clipped,
                "final_by_channel": {k: _money(v) for k, v in i.final_by_channel.items()},
            }
            for i in p.items
        ],
        "valid_count": p.valid_count,
        "skipped_count": p.skipped_count,
        "fingerprint": p.fingerprint,
        "min_price": _money(p.min_price),
        "conditional_deals": p.conditional_deals,
        "overlaps": p.overlaps,
    }


@router.post("/batch/apply")
async def batch_apply(req: BatchApplyRequest, session: AsyncSession = Depends(get_session)):
    """Aplica el lote revisado. Huella distinta → 409 sin escribir (Principio III)."""
    _require_ids(req.suggestion_ids)
    adapter = get_adapter(session)
    try:
        r = await suggestion_batch.apply_batch(
            session, adapter, req.suggestion_ids, req.fingerprint
        )
        if r.stale:
            raise HTTPException(status_code=409, detail=_STALE)
        await session.commit()
        return {
            "nights": [
                {
                    "date": n.date.isoformat(),
                    "suggestion_id": n.suggestion_id,
                    "status": n.status,
                    "reason": n.reason,
                }
                for n in r.nights
            ],
            "applied_count": r.applied_count,
            "skipped_count": r.skipped_count,
            "failed_count": r.failed_count,
            "suggestions": {str(k): v for k, v in r.suggestions.items()},
            "promotions": r.promotions,
        }
    finally:
        await adapter.aclose()


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
    adapter = get_adapter(session)
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
