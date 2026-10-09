"""Avisos al celular (feature 025): teléfonos registrados y registro de avisos enviados."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, _now


class PushDevice(Base, TimestampMixin):
    """Teléfono con la app instalada. El token es el identificador de avisos (FCM)."""

    __tablename__ = "push_device"

    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(16), default="android")
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notify_bookings: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_suggestions: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)


class PushNotificationLog(Base, TimestampMixin):
    """Aviso ya enviado: (tipo, referencia, huella) único → nunca se repite el mismo cambio."""

    __tablename__ = "push_notification_log"
    __table_args__ = (
        UniqueConstraint("kind", "ref", "fingerprint", name="uq_push_log_kind_ref_fp"),
    )

    kind: Mapped[str] = mapped_column(String(24))
    ref: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(80))
    sent: Mapped[int] = mapped_column(Integer, default=0)
