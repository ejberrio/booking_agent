"""Puerto de referencia de mercado + baseline simple (lee la tabla market_reference)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import MarketReference


class MarketProvider(Protocol):
    async def get(self, zone: str, day: date) -> Decimal | None: ...


class BaselineMarket:
    """Referencia simple: el último baseline registrado para la zona (vigente en `day`)."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, zone: str, day: date) -> Decimal | None:
        res = await self._session.execute(
            select(MarketReference)
            .where(MarketReference.zone == zone)
            .order_by(MarketReference.id.desc())
        )
        for ref in res.scalars():
            if (ref.valid_from is None or ref.valid_from <= day) and (
                ref.valid_to is None or day <= ref.valid_to
            ):
                return ref.reference_price
        return None
