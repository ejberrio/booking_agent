"""Proveedor de mercado GRATIS (feature 018): búsquedas dirigidas + extracción LLM.

Busca tarifas publicadas de la zona para el mes, extrae precios por noche con el
LLM y devuelve la MEDIANA con su nº de muestras. 0 muestras → None (el motor no
inventa). La ocupación de la zona no es obtenible gratis de forma fiable →
occupancy_pct siempre None (honesto; un proveedor pago la daría — ADR 0006).
"""

from __future__ import annotations

import json
import re
import statistics
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.market.provider import MarketSnapshot
from app.models.intelligence import MarketReference

_MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

_EXTRACT_PROMPT = (
    "De los siguientes resultados de búsqueda, extrae PRECIOS POR NOCHE en COP de "
    "APARTAMENTOS COMPLETOS de la zona indicada. Devuelve SOLO un array JSON de "
    "números (COP por noche, sin separadores). Omite habitaciones privadas, camas en "
    "hostal, precios por mes, por persona, en USD u otra moneda, o claramente de otra "
    "zona. Si no hay precios claros: []."
)


class TavilyMarketProvider:
    """Implementa MarketDataProvider sobre los puertos search + llm existentes."""

    def __init__(self, search, llm, *, session: AsyncSession | None = None):
        self._search = search
        self._llm = llm
        self._session = session  # opcional: persistir el snapshot en MarketReference

    async def get_snapshot(self, zone: str, month: date) -> MarketSnapshot | None:
        if self._llm is None:
            return None
        label = f"{_MONTHS_ES[month.month - 1]} {month.year}"
        query = f"precio por noche apartamento completo alquiler {zone} {label} airbnb booking"
        results = await self._search.search(query, max_results=5)
        prices = await self._extract_prices(zone, results)
        if not prices:
            return None
        adr = Decimal(int(statistics.median(prices)))
        snapshot = MarketSnapshot(
            zone=zone,
            month=month,
            adr=adr,
            occupancy_pct=None,
            sample_size=len(prices),
            source="tavily",
        )
        if self._session is not None:
            await self._persist(snapshot)
        return snapshot

    async def _extract_prices(self, zone: str, results) -> list[float]:
        if not results:
            return []
        blob = f"Zona: {zone}\n\n" + "\n\n".join(f"{r.title}\n{r.content}" for r in results)
        resp = await self._llm.chat(
            messages=[
                {"role": "system", "content": _EXTRACT_PROMPT},
                {"role": "user", "content": blob},
            ],
            tools=[],
            model=settings.llm_model,
        )
        content = resp.content or "[]"
        match = re.search(r"\[.*\]", content, re.DOTALL)
        raw = match.group(0) if match else "[]"
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            return []
        out: list[float] = []
        for v in values:
            try:
                price = float(v)
            except (TypeError, ValueError):
                continue
            # Filtro de cordura para COP por noche (descarta USD sueltos y basura).
            if 30_000 <= price <= 5_000_000:
                out.append(price)
        return out

    async def _persist(self, s: MarketSnapshot) -> None:
        month_end = (s.month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        existing = (
            await self._session.execute(
                select(MarketReference).where(
                    MarketReference.zone == s.zone,
                    MarketReference.source == "tavily",
                    MarketReference.valid_from == s.month,
                )
            )
        ).scalars().first()
        if existing is None:
            self._session.add(
                MarketReference(
                    zone=s.zone,
                    reference_price=s.adr,
                    source="tavily",
                    valid_from=s.month,
                    valid_to=month_end,
                    sample_size=s.sample_size,
                )
            )
        else:
            existing.reference_price = s.adr
            existing.sample_size = s.sample_size
        await self._session.flush()
