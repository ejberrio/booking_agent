"""Ajuste de precio por canal (feature 013).

El host define un recargo/descuento % por canal (p. ej. Airbnb +8%). Patrón
humano-en-el-bucle: preview (con fingerprint) → apply(confirm) → auditar
(ChannelOffsetLog) → verificar contra el Channel Manager (endpoint Alpha:
re-lectura; discrepancia ⇒ SyncIssue). El dominio habla en % y factor decimal;
la fórmula del multiplier vive en el adaptador (Principio II).
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelManager
from app.models.audit import ChannelOffsetLog
from app.models.calendar import Rate
from app.models.enums import ChangeOrigin, ChannelKind, SyncIssueKind
from app.models.property import Channel, Property
from app.models.sync import SyncIssue

# Canales gestionados por la app, en orden estable de presentación.
_MANAGED = [ChannelKind.booking, ChannelKind.airbnb]

_MIN_PCT = Decimal("-50")
_MAX_PCT = Decimal("100")

_EXAMPLE_FALLBACK = Decimal("100000")


class ChannelOffsetError(ValueError):
    """Error de dominio (mensaje apto para el host / loop del agente)."""


class FingerprintError(ChannelOffsetError):
    """La propuesta caducó o no corresponde al estado actual (re-preview)."""


def _fingerprint(channel: str, pct: Decimal, current: Decimal | None) -> str:
    raw = f"offset|{channel}|{pct}|{current}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _factor(pct: Decimal) -> Decimal | None:
    """% → factor multiplicativo para el CM. 0 = quitar el ajuste."""
    if pct == 0:
        return None
    return (Decimal("1") + pct / Decimal("100")).quantize(Decimal("0.0001"))


def _round_cop(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _validate_pct(pct: Decimal) -> Decimal:
    pct = Decimal(pct).quantize(Decimal("0.01"))
    if pct < _MIN_PCT or pct > _MAX_PCT:
        raise ChannelOffsetError(
            f"el ajuste debe estar entre {_MIN_PCT}% y {_MAX_PCT}% (recibido {pct}%)"
        )
    return pct


def _validate_channel(adapter: ChannelManager, channel: str) -> ChannelKind:
    try:
        kind = ChannelKind(channel)
    except ValueError as exc:
        raise ChannelOffsetError(f"canal desconocido: {channel}") from exc
    if kind not in _MANAGED:
        raise ChannelOffsetError(f"canal no gestionado: {channel}")
    if not adapter.supports_price_adjustment(channel):
        raise ChannelOffsetError(
            f"{kind.value} vende al precio base: su ajuste no es configurable en el "
            "Channel Manager. Ajusta el precio base o el offset de Airbnb."
        )
    return kind


async def _property(session: AsyncSession) -> Property:
    prop = (await session.execute(select(Property))).scalars().first()
    if prop is None or not prop.external_ref:
        raise ChannelOffsetError("no hay propiedad sincronizada; importa desde el Channel Manager")
    return prop


async def _channel_row(session: AsyncSession, kind: ChannelKind) -> Channel:
    ch = (
        await session.execute(select(Channel).where(Channel.kind == kind))
    ).scalars().first()
    if ch is None:
        raise ChannelOffsetError(
            f"el canal {kind.value} no está registrado; ejecuta una sincronización primero"
        )
    return ch


async def _example_base(session: AsyncSession, today: date) -> Decimal:
    """Precio base de ejemplo: primera fecha >= hoy con precio; fallback fijo."""
    rate = (
        await session.execute(
            select(Rate).where(Rate.date >= today).order_by(Rate.date).limit(1)
        )
    ).scalars().first()
    if rate is None:
        rate = (await session.execute(select(Rate).order_by(Rate.date).limit(1))).scalars().first()
    return Decimal(rate.base_price) if rate is not None else _EXAMPLE_FALLBACK


async def get_offsets(session: AsyncSession, adapter: ChannelManager) -> list[dict]:
    rows = (await session.execute(select(Channel))).scalars().all()
    by_kind = {c.kind: c for c in rows}
    out: list[dict] = []
    for kind in _MANAGED:
        ch = by_kind.get(kind)
        pct = ch.price_offset_pct if ch is not None else None
        out.append(
            {
                "channel": kind.value,
                "offset_pct": float(pct) if pct is not None else None,
                "supported": adapter.supports_price_adjustment(kind.value),
                "is_active": bool(ch.is_active) if ch is not None else False,
            }
        )
    return out


async def preview_offset(
    session: AsyncSession,
    adapter: ChannelManager,
    channel: str,
    pct: Decimal,
    *,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    kind = _validate_channel(adapter, channel)
    pct = _validate_pct(pct)
    ch = await _channel_row(session, kind)

    base = await _example_base(session, today)
    effective = _round_cop(base * (Decimal("1") + pct / Decimal("100")))
    warnings: list[str] = []
    if not ch.is_active:
        warnings.append(
            f"el canal {kind.value} está inactivo: el ajuste no tendrá efecto hasta reactivarlo"
        )
    current = ch.price_offset_pct
    return {
        "channel": kind.value,
        "current_pct": str(current) if current is not None else None,
        "new_pct": str(pct.normalize()),
        "example": {"base": str(_round_cop(base)), "effective": str(effective)},
        "warnings": warnings,
        "fingerprint": _fingerprint(kind.value, pct, current),
    }


async def apply_offset(
    session: AsyncSession,
    adapter: ChannelManager,
    channel: str,
    pct: Decimal,
    *,
    fingerprint: str | None,
    origin: ChangeOrigin,
    today: date | None = None,
) -> dict:
    kind = _validate_channel(adapter, channel)
    pct = _validate_pct(pct)
    ch = await _channel_row(session, kind)
    before = ch.price_offset_pct

    # fingerprint=None = vía del agente: su gate humano es el confirm del chat
    # (patrón de la feature 011). La vía web/API SIEMPRE manda fingerprint.
    if fingerprint is not None and fingerprint != _fingerprint(kind.value, pct, before):
        raise FingerprintError(
            "la propuesta no corresponde al estado actual; vuelve a previsualizar"
        )

    prop = await _property(session)
    factor = _factor(pct)
    result = await adapter.set_channel_price_adjustment(prop.external_ref, kind.value, factor)

    if not result.ok:
        session.add(
            SyncIssue(
                kind=SyncIssueKind.comm_error,
                entity_ref=f"channel:{kind.value}",
                detail=f"fallo al escribir el ajuste de precio: {result.detail or 'sin detalle'}",
            )
        )
        await session.flush()
        raise ChannelOffsetError(
            f"el Channel Manager rechazó el ajuste ({result.detail or 'sin detalle'}); "
            "no se aplicó nada"
        )

    ch.price_offset_pct = pct
    session.add(
        ChannelOffsetLog(
            channel_id=ch.id,
            before_pct=before,
            after_pct=pct,
            origin=origin,
            detail={
                "factor_sent": str(factor) if factor is not None else None,
                "verified": result.verified,
                "cm_detail": result.detail,
            },
        )
    )
    issue_detail: str | None = None
    if not result.verified:
        issue_detail = result.detail or "la relectura del Channel Manager no confirmó el valor"
        session.add(
            SyncIssue(
                kind=SyncIssueKind.write_unverified,
                entity_ref=f"channel:{kind.value}",
                detail=f"ajuste de precio aplicado pero no verificado: {issue_detail}",
            )
        )
    await session.flush()
    return {
        "applied": True,
        "verified": result.verified,
        "channel": kind.value,
        "offset_pct": float(pct),
        "issue": issue_detail,
    }
