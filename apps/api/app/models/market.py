from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import EventKind, Relevance, SuggestionStatus
from app.models.mixins import JSONBType, TimestampMixin


class Event(Base, TimestampMixin):
    """Evento de la ciudad. dedup_key garantiza idempotencia (sin duplicados)."""

    __tablename__ = "event"

    name: Mapped[str] = mapped_column(String(300))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    kind: Mapped[EventKind] = mapped_column(Enum(EventKind))
    relevance: Mapped[Relevance] = mapped_column(Enum(Relevance), default=Relevance.medium)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(400), unique=True, index=True)


class PriceSuggestion(Base, TimestampMixin):
    """Sugerencia del agente. Estados: proposed→approved→applied | proposed→rejected."""

    __tablename__ = "price_suggestion"

    property_id: Mapped[int] = mapped_column(ForeignKey("property.id"), index=True)
    unit_type_id: Mapped[int | None] = mapped_column(ForeignKey("unit_type.id"), nullable=True)
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    suggested_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rationale: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus), default=SuggestionStatus.proposed
    )
    # Enlace al cambio aplicado (id de price_change_log). Sin FK para evitar
    # dependencia circular price_suggestion <-> price_change_log.
    applied_change_id: Mapped[int | None] = mapped_column(nullable=True)
