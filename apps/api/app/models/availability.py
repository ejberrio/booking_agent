from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ChangeOrigin
from app.models.mixins import TimestampMixin, _now


class AvailabilityChangeLog(Base, TimestampMixin):
    """Bitácora append-only de cambios de disponibilidad (bloquear/abrir). Nunca se actualiza."""

    __tablename__ = "availability_change_log"

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    old_units_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_units_available: Mapped[int] = mapped_column(Integer)
    was_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[ChangeOrigin] = mapped_column(Enum(ChangeOrigin))
    message_id: Mapped[int | None] = mapped_column(ForeignKey("message.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
