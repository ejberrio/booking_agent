from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PromotionStatus, PromotionType
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
