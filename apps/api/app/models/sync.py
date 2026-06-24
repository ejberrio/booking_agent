from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    ConnectionStatus,
    IssueStatus,
    Provider,
    SyncDirection,
    SyncIssueKind,
    SyncStatus,
)
from app.models.mixins import TimestampMixin, _now


class ChannelManagerConnection(Base, TimestampMixin):
    """Cuenta de Channel Manager conectada (single-tenant: una activa)."""

    __tablename__ = "channel_manager_connection"

    provider: Mapped[Provider] = mapped_column(Enum(Provider), default=Provider.beds24)
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus), default=ConnectionStatus.unconfigured
    )
    # Nombre de la variable de entorno, NUNCA el secreto.
    credentials_ref: Mapped[str] = mapped_column(String(120), default="BEDS24_API_KEY")
    account_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SyncRun(Base, TimestampMixin):
    __tablename__ = "sync_run"

    direction: Mapped[SyncDirection] = mapped_column(Enum(SyncDirection))
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), default=SyncStatus.running)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    cursor: Mapped[str | None] = mapped_column(String(120), nullable=True)


class SyncIssue(Base, TimestampMixin):
    __tablename__ = "sync_issue"

    sync_run_id: Mapped[int | None] = mapped_column(ForeignKey("sync_run.id"), nullable=True)
    kind: Mapped[SyncIssueKind] = mapped_column(Enum(SyncIssueKind))
    entity_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    detail: Mapped[str] = mapped_column(Text)
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus), default=IssueStatus.open)
