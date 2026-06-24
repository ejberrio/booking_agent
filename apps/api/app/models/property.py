from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ChannelKind, PropertyStatus
from app.models.mixins import TimestampMixin


class Property(Base, TimestampMixin):
    __tablename__ = "property"

    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120), default="Medellín")
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus), default=PropertyStatus.active
    )

    channels: Mapped[list[Channel]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )
    unit_types: Mapped[list[UnitType]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )


class Channel(Base, TimestampMixin):
    __tablename__ = "channel"
    __table_args__ = (UniqueConstraint("property_id", "kind", name="uq_channel_property_kind"),)

    property_id: Mapped[int] = mapped_column(ForeignKey("property.id"))
    kind: Mapped[ChannelKind] = mapped_column(Enum(ChannelKind))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Channel-aware: modelado pero NO aplicado todavía.
    price_offset_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    property: Mapped[Property] = relationship(back_populates="channels")


class UnitType(Base, TimestampMixin):
    __tablename__ = "unit_type"

    property_id: Mapped[int] = mapped_column(ForeignKey("property.id"))
    name: Mapped[str] = mapped_column(String(200))
    units_count: Mapped[int] = mapped_column(default=1)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)

    property: Mapped[Property] = relationship(back_populates="unit_types")
