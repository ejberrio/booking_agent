"""Bitácora mínima de avisos entrantes (feature 020).

Jamás guarda el cuerpo ni las cabeceras del aviso: el de Beds24 trae datos
personales y tokens de pago. Solo resultado, referencia de la reserva y un
motivo FIJO. Se purga a los 30 días.
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.enums import WebhookResult
from app.models.mixins import TimestampMixin, _now


class WebhookEvent(Base, AccountOwned, TimestampMixin):
    __tablename__ = "webhook_event"

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    source: Mapped[str] = mapped_column(String(20), default="beds24")
    result: Mapped[WebhookResult] = mapped_column(
        Enum(WebhookResult, native_enum=False, length=10)
    )
    booking_ref: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sync_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
