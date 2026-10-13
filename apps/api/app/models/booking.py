from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.enums import BookingStatus, ChannelKind
from app.models.mixins import TimestampMixin


class Booking(Base, AccountOwned, TimestampMixin):
    """Reserva proveniente de un canal. Reduce la disponibilidad de la unidad."""

    __tablename__ = "booking"
    # Único por cuenta (feature 020 → 026): un aviso y el cron simultáneos no duplican.
    __table_args__ = (
        UniqueConstraint("account_id", "external_ref", name="uq_booking_account_external_ref"),
    )

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    channel_kind: Mapped[ChannelKind] = mapped_column(Enum(ChannelKind))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.confirmed
    )
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Dato personal: solo se muestra dentro de la app de su cuenta; nunca en logs.
    guest_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
