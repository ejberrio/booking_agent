from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ChannelKind, PromotionStatus, PromotionType
from app.models.mixins import JSONBType, TimestampMixin


class PricingRule(Base, TimestampMixin):
    __tablename__ = "pricing_rule"

    property_id: Mapped[int] = mapped_column(ForeignKey("property.id"), index=True)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Placeholder: paridad avanzada aplazada.
    parity_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Promotion(Base, TimestampMixin):
    __tablename__ = "promotion"

    property_id: Mapped[int] = mapped_column(ForeignKey("property.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    discount_type: Mapped[PromotionType] = mapped_column(Enum(PromotionType))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    conditions: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    status: Mapped[PromotionStatus] = mapped_column(
        Enum(PromotionStatus), default=PromotionStatus.active
    )
    # --- Vía "oferta" (feature 011): promo publicada como fixed price sobre una oferta ---
    # Cuando offer_id está poblado, la promo se publica al Channel Manager como un
    # fixed price sobre esa oferta (no como recorte del precio base). external_id es
    # el id del fixed price en el canal (necesario para editar/retirar). unit_type_id
    # acota la promo a una habitación (la vía oferta trabaja por habitación).
    unit_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("unit_type.id"), index=True, nullable=True
    )
    offer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class NativeDeal(Base, TimestampMixin):
    """Registro informativo de un deal nativo gestionado en el panel del canal.

    Los deals nativos (badge de Booking, semanal/mensual de Airbnb) no tienen API:
    el host los anota aquí para verlos en el calendario y para la advertencia real
    de doble descuento. NUNCA se escribe nada al canal desde este registro.
    date_from/date_to en NULL = extremo abierto (ambos NULL = "siempre activo").
    """

    __tablename__ = "native_deal"

    channel: Mapped[ChannelKind] = mapped_column(Enum(ChannelKind))
    name: Mapped[str] = mapped_column(String(120))
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Feature 022: "always" = puede aplicar a cualquier reserva (p. ej. móvil) y cuenta
    # para el precio mínimo; "conditional" = depende de la estadía/anticipación (informativo).
    stacking: Mapped[str] = mapped_column(String(12), default="conditional")
