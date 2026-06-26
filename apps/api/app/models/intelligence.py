from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SyncStatus
from app.models.mixins import TimestampMixin, _now


class MarketReference(Base, TimestampMixin):
    """Referencia de precio de mercado por zona (baseline simple en v1)."""

    __tablename__ = "market_reference"

    zone: Mapped[str] = mapped_column(String(120), index=True)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    source: Mapped[str] = mapped_column(String(60), default="baseline")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class IntelligenceRun(Base, TimestampMixin):
    """Una corrida del escaneo (eventos + mercado + sugerencias)."""

    __tablename__ = "intelligence_run"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), default=SyncStatus.running)
    events_found: Mapped[int] = mapped_column(Integer, default=0)
    suggestions_created: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
