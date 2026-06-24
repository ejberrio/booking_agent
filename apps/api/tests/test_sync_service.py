from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.channels.base import (
    ConnectionInfo,
    RemoteBooking,
    RemoteProperty,
    RemoteRate,
    RemoteRoom,
    WriteResult,
)
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.enums import SyncIssueKind
from app.models.property import Property, UnitType
from app.models.sync import SyncIssue
from app.services import sync_service

D = Decimal
DAY = date(2026, 7, 15)


class FakeCM:
    """Channel Manager falso in-memory que cumple el puerto."""

    def __init__(self, *, rates=None, bookings=None, write_verified=True):
        self.properties = [
            RemoteProperty("337229", "Apto", "COP", [RemoteRoom("697411", "3BR", 1)])
        ]
        self._rates = rates if rates is not None else [RemoteRate("697411", DAY, D("180000"), 1)]
        self._bookings = bookings or []
        self.write_verified = write_verified

    async def test_connection(self):
        return ConnectionInfo(True, self.properties)

    async def get_properties(self):
        return self.properties

    async def get_rates(self, room, df, dt):
        return [r for r in self._rates if r.room_external_id == room]

    async def get_bookings(self, prop, since=None):
        return self._bookings

    async def set_rate(self, room, day, price):
        return await self.set_rate_range(room, day, day, price)

    async def set_rate_range(self, room, df, dt, price):
        return WriteResult(True, self.write_verified, None if self.write_verified else "no verif")


async def _count(session, model) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_import_upserts_without_audit_and_idempotent(session):
    fake = FakeCM()
    run1 = await sync_service.import_remote(session, fake, DAY, DAY)
    assert await _count(session, Property) == 1
    assert await _count(session, UnitType) == 1
    rate = (await session.execute(select(Rate))).scalar_one()
    assert rate.base_price == D("180000")
    cd = (await session.execute(select(CalendarDay))).scalar_one()
    assert cd.units_available == 1
    assert await _count(session, PriceChangeLog) == 0  # baseline NO auditado
    assert run1.cursor == DAY.isoformat()

    # idempotente: segunda corrida no duplica
    run2 = await sync_service.import_remote(session, fake, DAY, DAY)
    assert await _count(session, Property) == 1
    assert await _count(session, Rate) == 1
    assert run2.created_count == 0
    assert run2.issue_count == 0


async def test_remote_availability_and_booking(session):
    fake = FakeCM(
        rates=[RemoteRate("697411", DAY, D("180000"), 0)],
        bookings=[RemoteBooking("555", "697411", DAY, date(2026, 7, 18))],
    )
    await sync_service.import_remote(session, fake, DAY, DAY)
    cd = (await session.execute(select(CalendarDay))).scalar_one()
    assert cd.units_available == 0  # remoto es fuente de verdad
    bk = (await session.execute(select(Booking))).scalar_one()
    assert bk.external_ref == "555"


async def test_price_discrepancy_opens_issue(session):
    fake = FakeCM()
    await sync_service.import_remote(session, fake, DAY, DAY)  # baseline 180000
    fake._rates = [RemoteRate("697411", DAY, D("200000"), 1)]  # el remoto cambia
    run = await sync_service.import_remote(session, fake, DAY, DAY)
    assert run.issue_count == 1
    issue = (await session.execute(select(SyncIssue))).scalars().first()
    assert issue.kind is SyncIssueKind.price_discrepancy
    rate = (await session.execute(select(Rate))).scalar_one()
    assert rate.base_price == D("180000")  # NO se sobrescribe


async def test_publish_unverified_opens_issue(session):
    await sync_service.import_remote(session, FakeCM(), DAY, DAY)  # crea la unidad
    unit = (await session.execute(select(UnitType))).scalar_one()
    run = await sync_service.publish_price(
        session,
        FakeCM(write_verified=False),
        unit_type_id=unit.id,
        date_from=DAY,
        date_to=DAY,
        price=D("250000"),
    )
    assert run.issue_count == 1
    issue = (
        await session.execute(
            select(SyncIssue).where(SyncIssue.kind == SyncIssueKind.write_unverified)
        )
    ).scalars().first()
    assert issue is not None


async def test_publish_verified_success(session):
    await sync_service.import_remote(session, FakeCM(), DAY, DAY)
    unit = (await session.execute(select(UnitType))).scalar_one()
    run = await sync_service.publish_price(
        session,
        FakeCM(write_verified=True),
        unit_type_id=unit.id,
        date_from=DAY,
        date_to=DAY,
        price=D("250000"),
    )
    assert run.status.value == "success"
    assert run.issue_count == 0
