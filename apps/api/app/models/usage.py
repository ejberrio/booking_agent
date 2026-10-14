"""Uso de IA por cuenta y día (feature 027): base de la medición, los límites y el panel."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.mixins import TimestampMixin


class AIUsage(Base, AccountOwned, TimestampMixin):
    """Acumulado diario. `kind`: chat_message (mensaje del anfitrión), chat (llamada del
    asistente), scan (llamada del escaneo), search (búsqueda web). `model` vacío si no aplica."""

    __tablename__ = "ai_usage"
    __table_args__ = (
        UniqueConstraint("account_id", "day", "kind", "model", name="uq_ai_usage_day_kind_model"),
    )

    day: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(80), default="")
    calls: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    unpriced: Mapped[int] = mapped_column(Integer, default=0)  # llamadas sin precio conocido
