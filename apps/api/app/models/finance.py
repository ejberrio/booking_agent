"""Rentabilidad mensual (feature 042): costos de la unidad y tasas de cambio."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.mixins import TimestampMixin


class UnitFinance(Base, AccountOwned, TimestampMixin):
    """Lo que el anfitrión declara para comparar la renta corta con un arriendo tradicional."""

    __tablename__ = "unit_finance"
    __table_args__ = (UniqueConstraint("unit_type_id", name="uq_unit_finance_unit"),)

    unit_type_id: Mapped[int] = mapped_column(ForeignKey("unit_type.id"), index=True)
    # Arriendo mensual de referencia (lo que daría un arriendo tradicional), en la moneda local.
    reference_rent: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Costos fijos al mes que en un arriendo tradicional pagaría el inquilino: servicios,
    # internet, administración, software (Beds24), reposición…
    fixed_costs: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Aseo por estancia (lo que paga el anfitrión, aunque el huésped pague tarifa de limpieza).
    cleaning_per_stay: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)


class FxRate(Base, TimestampMixin):
    """Tasa de cambio a la moneda local por día (TRM del Banco de la República para USD→COP).

    Dato público de plataforma: no pertenece a ninguna cuenta.
    """

    __tablename__ = "fx_rate"
    __table_args__ = (UniqueConstraint("currency", "quote", "day", name="uq_fx_rate"),)

    currency: Mapped[str] = mapped_column(String(3))  # p. ej. USD
    quote: Mapped[str] = mapped_column(String(3), default="COP")
    day: Mapped[date] = mapped_column(Date, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    source: Mapped[str] = mapped_column(String(40), default="trm")
