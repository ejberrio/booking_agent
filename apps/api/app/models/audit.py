from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ChangeOrigin
from app.models.mixins import TimestampMixin, _now


class PriceChangeLog(Base, TimestampMixin):
    """Bitácora append-only de cambios de precio. Nunca se actualiza ni borra."""

    __tablename__ = "price_change_log"

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    new_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    origin: Mapped[ChangeOrigin] = mapped_column(Enum(ChangeOrigin))
    suggestion_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_suggestion.id"), nullable=True
    )
    message_id: Mapped[int | None] = mapped_column(ForeignKey("message.id"), nullable=True)
    reverts_change_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_change_log.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
