"""Orquestación de sincronización con el Channel Manager (depende del puerto).

Reutiliza los modelos de la feature 001. Reglas:
- Importación de baseline: upsert de Rate/CalendarDay SIN auditar.
- Discrepancia de precio (local != remoto): se abre SyncIssue, NO se sobrescribe.
- Reservas/disponibilidad: el remoto es fuente de verdad.
- Publicación: el precio local ya fue auditado por pricing_service; aquí se publica
  y se abre SyncIssue si la escritura no se verifica.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelManager, RemoteFixedPrice
from app.channels.errors import AuthError, ChannelError
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.enums import (
    BookingStatus,
    ChannelKind,
    ConnectionStatus,
    IssueStatus,
    SyncDirection,
    SyncIssueKind,
    SyncStatus,
)
from app.core.config import settings
from app.models.mixins import _now
from app.models.property import Channel, Property, UnitType
from app.models.sync import ChannelManagerConnection, SyncIssue, SyncRun


def _map_channel(token: str | None) -> ChannelKind:
    """Token neutro del puerto → ChannelKind. Desconocido/ausente = direct.

    Nunca lanza: un origen no contemplado no puede abortar el lote (FR-002).
    """
    if token:
        t = token.strip().lower()
        if t.startswith("booking"):
            return ChannelKind.booking
        if t.startswith("airbnb"):
            return ChannelKind.airbnb
    return ChannelKind.direct


async def _upsert_channels(session: AsyncSession, prop: Property) -> None:
    """Sincroniza las filas Channel con la configuración (CHANNELS_ACTIVE).

    Los kinds configurados quedan activos; los registrados que salieron de la
    config quedan inactivos (sus reservas históricas se conservan).
    """
    configured = set(settings.active_channel_kinds())
    res = await session.execute(select(Channel).where(Channel.property_id == prop.id))
    existing = {c.kind: c for c in res.scalars()}
    for kind in configured:
        if kind in existing:
            existing[kind].is_active = True
        else:
            session.add(Channel(property_id=prop.id, kind=kind, is_active=True))
    for kind, channel in existing.items():
        if kind not in configured:
            channel.is_active = False
    await session.flush()


# --------- helpers de upsert por external_ref ---------


async def _get_connection(session: AsyncSession) -> ChannelManagerConnection:
    res = await session.execute(
        select(ChannelManagerConnection).where(ChannelManagerConnection.is_active.is_(True))
    )
    conn = res.scalars().first()
    if conn is None:
        conn = ChannelManagerConnection()
        session.add(conn)
        await session.flush()
    return conn


async def _upsert_property(session: AsyncSession, rp) -> Property:
    res = await session.execute(select(Property).where(Property.external_ref == rp.external_id))
    prop = res.scalar_one_or_none()
    if prop is None:
        prop = Property(name=rp.name, currency=rp.currency, external_ref=rp.external_id)
        session.add(prop)
        await session.flush()
    else:
        prop.name = rp.name
        prop.currency = rp.currency
    # Ubicación (feature 018): el remoto corrige cuando habla; su silencio no borra.
    if getattr(rp, "address", None):
        prop.address = rp.address
    if getattr(rp, "latitude", None) is not None:
        prop.latitude = rp.latitude
    if getattr(rp, "longitude", None) is not None:
        prop.longitude = rp.longitude
    # Canales conectados: desde configuración, no hardcoded (feature 012).
    await _upsert_channels(session, prop)
    await session.flush()
    return prop


async def _upsert_unit(session: AsyncSession, prop: Property, ext_id: str, name: str, qty: int) -> UnitType:
    res = await session.execute(select(UnitType).where(UnitType.external_ref == ext_id))
    unit = res.scalar_one_or_none()
    if unit is None:
        unit = UnitType(property_id=prop.id, name=name, units_count=qty, external_ref=ext_id)
        session.add(unit)
    else:
        unit.name = name
        unit.units_count = qty
    await session.flush()
    return unit


async def _get_rate(session: AsyncSession, unit_id: int, day: date) -> Rate | None:
    res = await session.execute(
        select(Rate).where(Rate.unit_type_id == unit_id, Rate.date == day)
    )
    return res.scalar_one_or_none()


async def _upsert_calendar(session: AsyncSession, unit_id: int, day: date, available: int) -> None:
    res = await session.execute(
        select(CalendarDay).where(CalendarDay.unit_type_id == unit_id, CalendarDay.date == day)
    )
    cd = res.scalar_one_or_none()
    if cd is None:
        session.add(CalendarDay(unit_type_id=unit_id, date=day, units_available=available))
    else:
        cd.units_available = available
    await session.flush()


# --------- operaciones públicas ---------


async def test_connection(
    session: AsyncSession, adapter: ChannelManager
) -> ChannelManagerConnection:
    conn = await _get_connection(session)
    try:
        info = await adapter.test_connection()
        conn.status = ConnectionStatus.connected if info.ok else ConnectionStatus.invalid
        conn.last_verified_at = _now()
        if info.properties:
            conn.account_label = info.properties[0].name
    except AuthError:
        conn.status = ConnectionStatus.invalid
    except ChannelError:
        conn.status = ConnectionStatus.invalid
    await session.flush()
    return conn


async def import_remote(
    session: AsyncSession,
    adapter: ChannelManager,
    date_from: date,
    date_to: date,
) -> SyncRun:
    """Sincronización entrante: upsert local, baseline sin auditar, discrepancias → issue."""
    run = SyncRun(direction=SyncDirection.inbound, status=SyncStatus.running)
    session.add(run)
    await session.flush()

    created = updated = issues = 0
    props = await adapter.get_properties()
    for rp in props:
        prop = await _upsert_property(session, rp)
        units_by_room: dict[str, UnitType] = {}
        for room in rp.rooms:
            unit = await _upsert_unit(session, prop, room.external_id, room.name, room.units_count)
            units_by_room[room.external_id] = unit

            for rate in await adapter.get_rates(room.external_id, date_from, date_to):
                existing = await _get_rate(session, unit.id, rate.date)
                # Sin precio remoto (0) NO se guarda como precio 0 (feature 023).
                if rate.price <= 0:
                    pass
                elif existing is None:
                    session.add(
                        Rate(unit_type_id=unit.id, date=rate.date, base_price=rate.price)
                    )
                    created += 1
                elif existing.base_price <= 0:
                    # Fila basura local (precio 0): el remoto es la línea base.
                    existing.base_price = rate.price
                    updated += 1
                elif existing.base_price != rate.price:
                    session.add(
                        SyncIssue(
                            sync_run_id=run.id,
                            kind=SyncIssueKind.price_discrepancy,
                            entity_ref=f"unit:{unit.id} date:{rate.date.isoformat()}",
                            detail=(
                                f"local={existing.base_price} remoto={rate.price}; "
                                "no se sobrescribe sin decisión del host"
                            ),
                        )
                    )
                    issues += 1
                await _upsert_calendar(session, unit.id, rate.date, rate.available)

        # Reservas: por propiedad, asignadas a su unidad, con su canal REAL de
        # origen. El remoto es fuente de verdad: re-importar corrige canal
        # (feature 012), nombre (016) y ESTADO/FECHAS (issue #91 — una
        # cancelación o modificación en el canal se refleja aquí; la
        # disponibilidad liberada llega sola por el calendario del CM).
        for rb in await adapter.get_bookings(rp.external_id):
            unit = units_by_room.get(rb.room_external_id)
            if unit is None:
                continue
            kind = _map_channel(rb.channel)
            status = (
                BookingStatus.cancelled if rb.status == "cancelled" else BookingStatus.confirmed
            )
            res = await session.execute(
                select(Booking).where(Booking.external_ref == rb.external_id)
            )
            existing_booking = res.scalar_one_or_none()
            if existing_booking is None:
                session.add(
                    Booking(
                        unit_type_id=unit.id,
                        channel_kind=kind,
                        check_in=rb.check_in,
                        check_out=rb.check_out,
                        status=status,
                        external_ref=rb.external_id,
                        guest_name=rb.guest_name,
                    )
                )
                created += 1
            else:
                changed = False
                if existing_booking.channel_kind != kind:
                    existing_booking.channel_kind = kind
                    changed = True
                if existing_booking.status != status:
                    existing_booking.status = status
                    changed = True
                if (existing_booking.check_in, existing_booking.check_out) != (
                    rb.check_in,
                    rb.check_out,
                ):
                    existing_booking.check_in = rb.check_in
                    existing_booking.check_out = rb.check_out
                    changed = True
                # El nombre se corrige solo si el remoto HABLA (su silencio no borra).
                if rb.guest_name and existing_booking.guest_name != rb.guest_name:
                    existing_booking.guest_name = rb.guest_name
                    changed = True
                if changed:
                    updated += 1

    run.created_count = created
    run.updated_count = updated
    run.issue_count = issues
    run.status = SyncStatus.partial if issues else SyncStatus.success
    run.finished_at = _now()
    run.cursor = date_to.isoformat()
    await session.flush()
    return run


async def reconcile(
    session: AsyncSession, adapter: ChannelManager, date_from: date, date_to: date
) -> SyncRun:
    """Reconciliación: misma lógica entrante (detecta discrepancias, sin overwrite)."""
    return await import_remote(session, adapter, date_from, date_to)


async def publish_price(
    session: AsyncSession,
    adapter: ChannelManager,
    *,
    unit_type_id: int,
    date_from: date,
    date_to: date,
    price,
) -> SyncRun:
    """Publica al remoto un precio que el host ya fijó y auditó localmente."""
    run = SyncRun(direction=SyncDirection.outbound, status=SyncStatus.running)
    session.add(run)
    await session.flush()

    unit = await session.get(UnitType, unit_type_id)
    if unit is None or not unit.external_ref:
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.comm_error,
                entity_ref=f"unit:{unit_type_id}",
                detail="La unidad no tiene external_ref (no mapeada al Channel Manager)",
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.error
        run.finished_at = _now()
        await session.flush()
        return run

    try:
        result = await adapter.set_rate_range(unit.external_ref, date_from, date_to, price)
    except ChannelError as exc:
        # La publicación falló (p. ej. credenciales/propKey): se registra incidencia,
        # el cambio local se conserva (no se tumba la operación).
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.comm_error,
                entity_ref=f"unit:{unit_type_id} {date_from}..{date_to}",
                detail=str(exc),
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.error
        run.finished_at = _now()
        await session.flush()
        return run
    if not result.verified:
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.write_unverified,
                entity_ref=f"unit:{unit_type_id} {date_from}..{date_to}",
                detail=result.detail or "escritura no verificada",
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.partial
    else:
        run.updated_count = (date_to - date_from).days + 1
        run.status = SyncStatus.success
    run.finished_at = _now()
    await session.flush()
    return run


async def publish_availability(
    session: AsyncSession,
    adapter: ChannelManager,
    *,
    unit_type_id: int,
    date_from: date,
    date_to: date,
    num_avail: int,
) -> SyncRun:
    """Publica al remoto la disponibilidad (numAvail) de un rango ya aplicado localmente."""
    run = SyncRun(direction=SyncDirection.outbound, status=SyncStatus.running)
    session.add(run)
    await session.flush()

    unit = await session.get(UnitType, unit_type_id)
    if unit is None or not unit.external_ref:
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.comm_error,
                entity_ref=f"unit:{unit_type_id}",
                detail="La unidad no tiene external_ref (no mapeada al Channel Manager)",
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.error
        run.finished_at = _now()
        await session.flush()
        return run

    try:
        result = await adapter.set_availability_range(
            unit.external_ref, date_from, date_to, num_avail
        )
    except ChannelError as exc:
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.comm_error,
                entity_ref=f"unit:{unit_type_id} {date_from}..{date_to}",
                detail=str(exc),
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.error
        run.finished_at = _now()
        await session.flush()
        return run
    if not result.verified:
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.write_unverified,
                entity_ref=f"unit:{unit_type_id} {date_from}..{date_to}",
                detail=result.detail or "escritura no verificada",
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.partial
    else:
        run.updated_count = (date_to - date_from).days + 1
        run.status = SyncStatus.success
    run.finished_at = _now()
    await session.flush()
    return run


async def publish_promotion(
    session: AsyncSession, adapter: ChannelManager, fp: RemoteFixedPrice
) -> tuple[int | None, str | None]:
    """Publica una promoción como fixed price. Devuelve (external_id, issue_detail).

    issue_detail no-None indica fallo (se registró SyncIssue); el flujo NO se rompe.
    """
    run = SyncRun(direction=SyncDirection.outbound, status=SyncStatus.running)
    session.add(run)
    await session.flush()
    try:
        result = await adapter.set_fixed_price(fp)
    except ChannelError as exc:
        detail = str(exc)
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.comm_error,
                entity_ref=f"promo offer:{fp.offer_id} {fp.first_night}..{fp.last_night}",
                detail=detail,
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.error
        run.finished_at = _now()
        await session.flush()
        return (fp.external_id, detail)
    if not result.ok:
        detail = result.detail or "escritura de promoción no confirmada"
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.write_unverified,
                entity_ref=f"promo offer:{fp.offer_id} {fp.first_night}..{fp.last_night}",
                detail=detail,
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.partial
        run.finished_at = _now()
        await session.flush()
        return (result.external_id, detail)
    run.updated_count = 1
    run.status = SyncStatus.success
    run.finished_at = _now()
    await session.flush()
    return (result.external_id, None)


async def retire_promotion(
    session: AsyncSession, adapter: ChannelManager, *, external_id: int, room_external_id: str,
    offer_id: int,
) -> str | None:
    """Neutraliza una promoción (roomPriceEnable=false). Devuelve issue_detail o None."""
    run = SyncRun(direction=SyncDirection.outbound, status=SyncStatus.running)
    session.add(run)
    await session.flush()
    try:
        result = await adapter.disable_fixed_price(external_id, room_external_id)
    except ChannelError as exc:
        detail = str(exc)
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.comm_error,
                entity_ref=f"promo offer:{offer_id} fixedPrice:{external_id}",
                detail=detail,
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.error
        run.finished_at = _now()
        await session.flush()
        return detail
    if not result.ok:
        detail = result.detail or "retirada no confirmada"
        session.add(
            SyncIssue(
                sync_run_id=run.id,
                kind=SyncIssueKind.write_unverified,
                entity_ref=f"promo offer:{offer_id} fixedPrice:{external_id}",
                detail=detail,
            )
        )
        run.issue_count = 1
        run.status = SyncStatus.partial
        run.finished_at = _now()
        await session.flush()
        return detail
    run.updated_count = 1
    run.status = SyncStatus.success
    run.finished_at = _now()
    await session.flush()
    return None


async def list_open_issues(session: AsyncSession) -> list[SyncIssue]:
    res = await session.execute(
        select(SyncIssue).where(SyncIssue.status == IssueStatus.open).order_by(SyncIssue.id)
    )
    return list(res.scalars())
