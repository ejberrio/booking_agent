from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CalendarDay(Base, TimestampMixin):
    """Disponibilidad por unidad y día. Compartida entre canales (no por canal)."""

    __tablename__ = "calendar_day"
    __table_args__ = (UniqueConstraint("unit_type_id", "date", name="uq_calendarday_unit_date"),)

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    units_available: Mapped[int] = mapped_column(Integer, default=0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class CalendarNote(Base, TimestampMixin):
    """Nota de texto libre del host sobre un día o rango (feature 016).

    Memoria local del host (típico: el porqué de un bloqueo). Nunca toca el
    Channel Manager. Los rangos pueden solaparse sin límite.
    """

    __tablename__ = "calendar_note"

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    text: Mapped[str] = mapped_column(String(500))


class Rate(Base, TimestampMixin):
    """Precio base por noche, por unidad y día. El efectivo se deriva (no se persiste)."""

    __tablename__ = "rate"
    __table_args__ = (UniqueConstraint("unit_type_id", "date", name="uq_rate_unit_date"),)

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
