"""Registro de huéspedes para la TRA del MinCIT y SIRE de Migración (feature 046, #167).

Los datos de los huéspedes (documentos, nombres, ciudades…) se guardan CIFRADOS en
`data_encrypted` con una clave derivada por cuenta (registration_service). Solo los estados,
fechas y el código que devuelve el MinCIT quedan en claro. Nunca van a logs, avisos ni a la IA.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.mixins import TimestampMixin

# Estados del registro
PENDING = "pending"  # creado (enlace listo), sin datos
SUBMITTED = "submitted"  # el huésped (o el anfitrión) llenó los datos
TRA_SENT = "tra_sent"  # TRA aceptada para todos
TRA_PARTIAL = "tra_partial"  # el principal quedó, faltan acompañantes
TRA_ERROR = "tra_error"  # el MinCIT rechazó o no respondió


class GuestRegistration(Base, AccountOwned, TimestampMixin):
    __tablename__ = "guest_registration"
    __table_args__ = (UniqueConstraint("booking_id", name="uq_guest_registration_booking"),)

    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    # Enlace público /checkin/{token}: aleatorio, no derivable; único en toda la plataforma.
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=PENDING)
    # JSON cifrado (Fernet) con {"main": {...}, "companions": [...], "motivo": ..., "foreign": bool}
    data_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Quién llenó los datos: "guest" (enlace) u "host" (panel)
    filled_by: Mapped[str | None] = mapped_column(String(10), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Costo total reportado a la TRA (COP); None = se propone desde la reserva (042)
    cost_cop: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    # TRA: código del principal y resultado por acompañante [{"i": 0, "code": 7} | {"i": 1, "error": "…"}]
    tra_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tra_companions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tra_error: Mapped[str | None] = mapped_column(String(300), nullable=True)  # sin datos personales
    tra_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tra_sent_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # SIRE (entrega 2): marcado a mano por el anfitrión tras cargar el archivo
    sire_entry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sire_exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Retención (028): True cuando ya se borraron los datos (1 año tras la salida)
    purged: Mapped[bool] = mapped_column(Boolean, default=False)


class RegistrationSettings(Base, AccountOwned, TimestampMixin):
    """Datos del establecimiento para la TRA y SIRE. Una fila por cuenta. El token del
    MinCIT es un secreto de cuenta (`mincit_tra_token`), no vive aquí."""

    __tablename__ = "registration_settings"
    __table_args__ = (UniqueConstraint("account_id", name="uq_registration_settings_account"),)

    rnt: Mapped[str | None] = mapped_column(String(20), nullable=True)
    establishment_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Tipo de acomodación por unidad {unit_type_id: "Apartamento" | "Casa" | "Finca" | …}
    accommodation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sire_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sire_city: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Autorización del anfitrión para que StayLever envíe la TRA en su nombre (Res. 700 art. 5)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
