"""Servicio de sugerencias: máquina de estados y aplicación auditada."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import PriceChangeLog
from app.models.enums import ChangeOrigin, SuggestionStatus
from app.models.market import PriceSuggestion
from app.services.pricing_service import set_base_price


async def _get(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    s = await session.get(PriceSuggestion, suggestion_id)
    if s is None:
        raise ValueError(f"No existe la sugerencia {suggestion_id}")
    return s


async def approve(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    s = await _get(session, suggestion_id)
    if s.status is not SuggestionStatus.proposed:
        raise ValueError("Solo se aprueba una sugerencia 'proposed'")
    s.status = SuggestionStatus.approved
    await session.flush()
    return s


async def reject(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    s = await _get(session, suggestion_id)
    if s.status is not SuggestionStatus.proposed:
        raise ValueError("Solo se rechaza una sugerencia 'proposed'")
    s.status = SuggestionStatus.rejected
    await session.flush()
    return s


async def apply(
    session: AsyncSession, suggestion_id: int, *, message_id: int | None = None
) -> list[PriceChangeLog]:
    """Aplica una sugerencia (proposed/approved): fija el precio en su rango y la enlaza."""
    s = await _get(session, suggestion_id)
    if s.status not in (SuggestionStatus.proposed, SuggestionStatus.approved):
        raise ValueError("Solo se aplica una sugerencia 'proposed' o 'approved'")
    if s.unit_type_id is None:
        raise ValueError("La sugerencia no tiene unidad asignada")

    logs: list[PriceChangeLog] = []
    day = s.date_from
    while day <= s.date_to:
        log = await set_base_price(
            session,
            unit_type_id=s.unit_type_id,
            day=day,
            new_price=s.suggested_price,
            origin=ChangeOrigin.suggestion,
            property_id=s.property_id,
            suggestion_id=s.id,
            message_id=message_id,
            validate_rule=False,
        )
        logs.append(log)
        day += timedelta(days=1)

    s.status = SuggestionStatus.applied
    s.applied_change_id = logs[0].id
    await session.flush()
    return logs
