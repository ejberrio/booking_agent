"""Página pública e informe gratis (feature 030). Tablas de PLATAFORMA (no `AccountOwned`).

Ninguna guarda la IP del visitante: el límite diario usa un HMAC de la IP con la fecha
(`public_quota.visitor`), que cambia cada día. `public_report` no guarda correo ni nombre;
solo se vincula a la cuenta que se registra desde él.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, _now


class CityScan(Base):
    """Última búsqueda de eventos de una ciudad (`event.city`): caché del informe y del cron."""

    __tablename__ = "city_scan"

    city: Mapped[str] = mapped_column(String(80), primary_key=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    source: Mapped[str] = mapped_column(String(10), default="daily")  # daily | public
    events_found: Mapped[int] = mapped_column(Integer, default=0)


class PublicReport(Base, TimestampMixin):
    __tablename__ = "public_report"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    municipality_code: Mapped[str] = mapped_column(String(5))
    city: Mapped[str] = mapped_column(String(80))
    weekday_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    weekend_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    unit_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="es")
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id"), nullable=True, index=True
    )
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WaitlistEntry(Base, TimestampMixin):
    """Lista de espera de la beta: solo para avisar; se borra al invitar o a los 12 meses."""

    __tablename__ = "waitlist_entry"

    email: Mapped[str] = mapped_column(String(254), unique=True)
    language: Mapped[str] = mapped_column(String(2), default="es")
    municipality_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PublicMetric(Base):
    """Contadores diarios agregados (sin rastreo individual)."""

    __tablename__ = "public_metric"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class PublicQuota(Base):
    """Uso diario por visitante (HMAC diario de la IP) o por correo (HMAC del correo)."""

    __tablename__ = "public_quota"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    visitor: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
