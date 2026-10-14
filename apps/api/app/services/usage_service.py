"""Uso y límites de IA por cuenta (feature 027).

La medición vive en envoltorios de los puertos `LLM` y `SearchProvider` (principio II): se
instalan donde se usa la IA (chat y recorrido del cron por cuenta) con la sesión de esa
cuenta, así que todo queda atribuido a ella por el filtro automático (principio VI).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.account import Account
from app.models.usage import AIUsage

CHAT_MESSAGE = "chat_message"
CHAT = "chat"
SCAN = "scan"
SEARCH = "search"
WARN_RATIO = 0.8


def local_today(now: datetime | None = None) -> date:
    tz = ZoneInfo(settings.ai_timezone)
    return (now.astimezone(tz) if now else datetime.now(tz)).date()


def month_start(day: date) -> date:
    return day.replace(day=1)


def next_month(day: date) -> date:
    return date(day.year + (day.month == 12), day.month % 12 + 1, 1)


def _bare(model: str | None) -> str:
    return (model or "").split("/")[-1]


def llm_cost(model: str | None, input_tokens: int, output_tokens: int) -> Decimal | None:
    """USD estimados; None si el modelo no tiene precio configurado."""
    price = settings.ai_prices.get(_bare(model))
    if not isinstance(price, list | tuple) or len(price) != 2:
        return None
    return (Decimal(str(price[0])) * input_tokens + Decimal(str(price[1])) * output_tokens) / Decimal(
        1_000_000
    )


async def record(
    session: AsyncSession,
    kind: str,
    *,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    calls: int = 1,
    cost: Decimal | None = Decimal("0"),
    day: date | None = None,
) -> None:
    """Suma al acumulado del día de la cuenta del contexto (no hace commit)."""
    day = day or local_today()
    model_key = _bare(model)
    row = (
        await session.execute(
            select(AIUsage).where(AIUsage.day == day, AIUsage.kind == kind, AIUsage.model == model_key)
        )
    ).scalar_one_or_none()
    if row is None:
        row = AIUsage(day=day, kind=kind, model=model_key, calls=0, input_tokens=0,
                      output_tokens=0, cost_usd=Decimal("0"), unpriced=0)
        session.add(row)
    row.calls += calls
    row.input_tokens += input_tokens
    row.output_tokens += output_tokens
    if cost is None:
        row.unpriced += calls
    else:
        row.cost_usd = Decimal(row.cost_usd or 0) + cost
    await session.flush()


async def _sum_calls(session: AsyncSession, kind: str, start: date, end: date | None = None) -> int:
    stmt = select(func.coalesce(func.sum(AIUsage.calls), 0)).where(
        AIUsage.kind == kind, AIUsage.day >= start
    )
    if end is not None:
        stmt = stmt.where(AIUsage.day < end)
    return int((await session.execute(stmt)).scalar_one())


@dataclass
class ChatQuota:
    used: int
    limit: int
    resets_on: date

    @property
    def exhausted(self) -> bool:
        return self.used >= self.limit

    @property
    def warning(self) -> bool:
        return self.used >= self.limit * WARN_RATIO

    def as_dict(self) -> dict:
        return {"used": self.used, "limit": self.limit, "resets_on": self.resets_on.isoformat(),
                "warning": self.warning, "exhausted": self.exhausted}


async def chat_quota(session: AsyncSession, account_id: int, today: date | None = None) -> ChatQuota:
    today = today or local_today()
    acc = await session.get(Account, account_id)
    limit = acc.chat_limit_month if acc and acc.chat_limit_month is not None else settings.ai_chat_limit_month
    used = await _sum_calls(session, CHAT_MESSAGE, month_start(today), next_month(today))
    return ChatQuota(used=used, limit=limit, resets_on=next_month(today))


async def search_limit(session: AsyncSession, account_id: int) -> int:
    acc = await session.get(Account, account_id)
    return acc.search_limit_day if acc and acc.search_limit_day is not None else settings.ai_search_limit_day


async def searches_on(session: AsyncSession, day: date) -> int:
    return await _sum_calls(session, SEARCH, day, date.fromordinal(day.toordinal() + 1))


async def month_cost(session: AsyncSession, today: date | None = None) -> Decimal:
    today = today or local_today()
    stmt = select(func.coalesce(func.sum(AIUsage.cost_usd), 0)).where(
        AIUsage.day >= month_start(today), AIUsage.day < next_month(today)
    )
    return Decimal((await session.execute(stmt)).scalar_one() or 0)


# --------- medidores de los puertos ---------


class MeteredLLM:
    """Envuelve el puerto LLM: cada llamada suma tokens y costo a la cuenta de `session`."""

    def __init__(self, inner, session: AsyncSession, kind: str):
        self._inner, self._session, self._kind = inner, session, kind

    async def chat(self, *, messages: list[dict], tools: list[dict], model: str):
        resp = await self._inner.chat(messages=messages, tools=tools, model=model)
        tin, tout = resp.usage or (0, 0)
        used_model = resp.model or model
        await record(self._session, self._kind, model=used_model, input_tokens=tin,
                     output_tokens=tout, cost=llm_cost(used_model, tin, tout))
        return resp


class MeteredSearch:
    """Envuelve el puerto de búsqueda: cuenta cada búsqueda y respeta el tope diario."""

    def __init__(self, inner, session: AsyncSession, *, limit: int, day: date | None = None):
        self._inner, self._session, self._limit = inner, session, limit
        self._day = day or local_today()
        self.skipped = 0
        self._done: int | None = None

    async def search(self, query: str, *, max_results: int = 5):
        if self._done is None:
            self._done = await searches_on(self._session, self._day)
        if self._done >= self._limit:
            self.skipped += 1
            return []
        results = await self._inner.search(query, max_results=max_results)
        self._done += 1
        price = settings.ai_prices.get("search")
        await record(self._session, SEARCH, day=self._day,
                     cost=Decimal(str(price)) if isinstance(price, int | float) else None)
        return results
