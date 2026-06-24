"""Servicio de auditoría: rollback de cambios de precio con detección de conflicto."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import PriceChangeLog
from app.models.enums import ChangeOrigin
from app.services.pricing_service import set_base_price


class RollbackConflict(Exception):
    """Existen cambios posteriores sobre la misma (unidad, fecha); requiere confirmación."""

    def __init__(self, change_id: int, later_changes: int) -> None:
        self.change_id = change_id
        self.later_changes = later_changes
        super().__init__(
            f"El cambio {change_id} tiene {later_changes} cambio(s) posterior(es); "
            "confirme para sobrescribir."
        )


async def _later_changes_count(session: AsyncSession, target: PriceChangeLog) -> int:
    # Orden por id (monótono y append-only): un cambio posterior tiene id mayor.
    res = await session.execute(
        select(func.count())
        .select_from(PriceChangeLog)
        .where(
            PriceChangeLog.unit_type_id == target.unit_type_id,
            PriceChangeLog.date == target.date,
            PriceChangeLog.id > target.id,
        )
    )
    return int(res.scalar_one())


async def rollback_change(
    session: AsyncSession, change_id: int, *, confirm: bool = False
) -> PriceChangeLog:
    """Revierte un cambio creando uno nuevo (origin=rollback) con el valor anterior.

    Si existen cambios posteriores sobre la misma (unidad, fecha) y `confirm` es False,
    lanza RollbackConflict en lugar de sobrescribir en silencio.
    """
    target = await session.get(PriceChangeLog, change_id)
    if target is None:
        raise ValueError(f"No existe el cambio {change_id}")
    if target.old_price is None:
        raise ValueError(
            "El cambio objetivo no tiene valor anterior (creación); no se puede revertir."
        )

    later = await _later_changes_count(session, target)
    if later > 0 and not confirm:
        raise RollbackConflict(change_id, later)

    log = await set_base_price(
        session,
        unit_type_id=target.unit_type_id,
        day=target.date,
        new_price=target.old_price,
        origin=ChangeOrigin.rollback,
        validate_rule=False,
    )
    log.reverts_change_id = target.id
    await session.flush()
    return log
