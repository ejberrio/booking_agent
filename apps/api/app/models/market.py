from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.enums import EventKind, Relevance, SuggestionStatus
from app.models.mixins import JSONBType, TimestampMixin


class Event(Base, TimestampMixin):
    """Evento público de una ciudad, compartido entre cuentas (feature 026).

    (city, dedup_key) garantiza idempotencia (sin duplicados) por ciudad.
    """

    __tablename__ = "event"
    __table_args__ = (UniqueConstraint("city", "dedup_key", name="uq_event_city_dedup"),)

    name: Mapped[str] = mapped_column(String(300))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    kind: Mapped[EventKind] = mapped_column(Enum(EventKind))
    relevance: Mapped[Relevance] = mapped_column(Enum(Relevance), default=Relevance.medium)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(400), index=True)
    # Ciudad normalizada (minúsculas, sin tildes): ver event_service.normalize_city.
    city: Mapped[str] = mapped_column(String(80), default="medellin", index=True)


class PriceSuggestion(Base, AccountOwned, TimestampMixin):
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
    # Feature 022: promoción que aplicó una bajada (sin FK, como applied_change_id).
    applied_promotion_id: Mapped[int | None] = mapped_column(nullable=True)


class PointOfInterest(Base, AccountOwned, TimestampMixin):
    """Sitio relevante cercano a la propiedad (feature 018). Dirige las búsquedas del scan.

    date_from/date_to opcionales = fechas clave (p. ej. inauguración); NULL = siempre.
    """

    __tablename__ = "point_of_interest"

    name: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
