from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BookingStatus, ChannelKind
from app.models.mixins import TimestampMixin


class Booking(Base, TimestampMixin):
    """Reserva proveniente de un canal. Reduce la disponibilidad de la unidad."""

    __tablename__ = "booking"

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    channel_kind: Mapped[ChannelKind] = mapped_column(Enum(ChannelKind))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.confirmed
    )
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
