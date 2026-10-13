from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
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
    # Feature 018: ocupación de la zona (si el proveedor la da) y nº de muestras.
    occupancy_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)


class IntelligenceRun(Base, AccountOwned, TimestampMixin):
    """Una corrida del escaneo (eventos + mercado + sugerencias)."""

    __tablename__ = "intelligence_run"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), default=SyncStatus.running)
    events_found: Mapped[int] = mapped_column(Integer, default=0)
    suggestions_created: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanConfig(Base, AccountOwned, TimestampMixin):
    """Configuración del escaneo (una fila por cuenta; features 018 y 026).

    zone NULL = usar city + address de la propiedad; event_kinds NULL = todos.
    """

    __tablename__ = "scan_config"
    __table_args__ = (UniqueConstraint("account_id", name="uq_scan_config_account"),)

    zone: Mapped[str | None] = mapped_column(String(200), nullable=True)
    queries_per_scan: Mapped[int] = mapped_column(Integer, default=12)
    event_kinds: Mapped[str | None] = mapped_column(String(200), nullable=True)
