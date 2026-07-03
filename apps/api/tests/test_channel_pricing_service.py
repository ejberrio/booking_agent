"""Feature 013 · US1: servicio de ajuste de precio por canal (T006)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.channels.base import RemoteRate, WriteResult
from app.models.audit import ChannelOffsetLog
from app.models.calendar import Rate
from app.models.enums import ChangeOrigin, ChannelKind
from app.models.property import Channel, Property, UnitType
from app.models.sync import SyncIssue
from app.services import channel_pricing_service as svc

TODAY = date(2026, 7, 15)


class FakeCM:
    """Doble del puerto: solo lo que usa el servicio."""

    def __init__(self, *, factor=None, ok=True, verified=True, rates_price=D("350000")):
        self.factor = factor
        self.ok = ok
        self.verified = verified
        self.rates_price = rates_price
        self.set_calls: list[tuple[str, D | None]] = []

    def supports_price_adjustment(self, channel: str) -> bool:
        return channel == "airbnb"

    async def get_channel_price_adjustment(self, prop, channel):
        return self.factor

    async def set_channel_price_adjustment(self, prop, channel, factor):
        self.set_calls.append((channel, factor))
        if not self.ok:
            return WriteResult(False, False, "canal caído")
        if not self.verified:
            return WriteResult(True, False, "esperado X, leído Y")
        self.factor = factor
        return WriteResult(True, True, None)

    async def get_rates(self, room, df, dt):
        return [RemoteRate(room, df, self.rates_price, 1)]


async def _seed(session, *, airbnb_active=True, offset=None):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    session.add(
        Channel(
            property_id=prop.id,
            kind=ChannelKind.airbnb,
            is_active=airbnb_active,
            price_offset_pct=offset,
        )
    )
    session.add(Rate(unit_type_id=unit.id, date=TODAY, base_price=D("350000")))
    await session.flush()
    return prop


# --- get_offsets --------------------------------------------------------------


async def test_get_offsets_defaults(session):
    await _seed(session)
    out = await svc.get_offsets(session, FakeCM())
    by = {o["channel"]: o for o in out}
    assert by["booking"]["offset_pct"] is None
    assert by["booking"]["supported"] is False
    assert by["airbnb"]["offset_pct"] is None
    assert by["airbnb"]["supported"] is True


# --- preview -------------------------------------------------------------------


async def test_preview_shows_example_and_fingerprint(session):
    await _seed(session)
    p = await svc.preview_offset(session, FakeCM(), "airbnb", D("8"), today=TODAY)
    assert p["channel"] == "airbnb"
    assert p["current_pct"] is None
    assert p["new_pct"] == "8"
    assert p["example"]["base"] == "350000"
    assert p["example"]["effective"] == "378000"
    assert p["fingerprint"]


async def test_preview_warns_inactive_channel(session):
    await _seed(session, airbnb_active=False)
    p = await svc.preview_offset(session, FakeCM(), "airbnb", D("8"), today=TODAY)
    assert any("inactivo" in w for w in p["warnings"])


async def test_preview_rejects_out_of_range(session):
    await _seed(session)
    with pytest.raises(svc.ChannelOffsetError):
        await svc.preview_offset(session, FakeCM(), "airbnb", D("150"), today=TODAY)
    with pytest.raises(svc.ChannelOffsetError):
        await svc.preview_offset(session, FakeCM(), "airbnb", D("-60"), today=TODAY)


async def test_preview_honest_for_unsupported_channel(session):
    await _seed(session)
    with pytest.raises(svc.ChannelOffsetError) as exc:
        await svc.preview_offset(session, FakeCM(), "booking", D("5"), today=TODAY)
    assert "precio base" in str(exc.value)


# --- apply ---------------------------------------------------------------------


async def _preview_and_apply(session, cm, pct, origin=ChangeOrigin.manual):
    p = await svc.preview_offset(session, cm, "airbnb", pct, today=TODAY)
    return await svc.apply_offset(
        session, cm, "airbnb", pct, fingerprint=p["fingerprint"], origin=origin, today=TODAY
    )


async def test_apply_persists_audits_and_verifies(session):
    await _seed(session)
    cm = FakeCM()
    result = await _preview_and_apply(session, cm, D("8"))
    assert result["applied"] and result["verified"]
    # factor enviado al CM
    assert cm.set_calls == [("airbnb", D("1.08"))]
    # persistido
    ch = (
        await session.execute(select(Channel).where(Channel.kind == ChannelKind.airbnb))
    ).scalar_one()
    assert ch.price_offset_pct == D("8")
    # auditado
    log = (await session.execute(select(ChannelOffsetLog))).scalar_one()
    assert log.before_pct is None and log.after_pct == D("8")
    assert log.origin == ChangeOrigin.manual


async def test_apply_zero_reverts_and_audits(session):
    await _seed(session, offset=D("8"))
    cm = FakeCM(factor=D("1.08"))
    result = await _preview_and_apply(session, cm, D("0"), origin=ChangeOrigin.chat)
    assert result["applied"]
    assert cm.set_calls == [("airbnb", None)]  # 0 = quitar el factor
    ch = (
        await session.execute(select(Channel).where(Channel.kind == ChannelKind.airbnb))
    ).scalar_one()
    assert ch.price_offset_pct == D("0")
    log = (await session.execute(select(ChannelOffsetLog))).scalar_one()
    assert log.before_pct == D("8") and log.after_pct == D("0")
    assert log.origin == ChangeOrigin.chat


async def test_apply_requires_valid_fingerprint(session):
    await _seed(session)
    with pytest.raises(svc.ChannelOffsetError):
        await svc.apply_offset(
            session, FakeCM(), "airbnb", D("8"),
            fingerprint="nope", origin=ChangeOrigin.manual, today=TODAY,
        )


async def test_apply_failure_opens_issue_and_does_not_persist(session):
    await _seed(session)
    cm = FakeCM(ok=False)
    with pytest.raises(svc.ChannelOffsetError):
        await _preview_and_apply(session, cm, D("8"))
    ch = (
        await session.execute(select(Channel).where(Channel.kind == ChannelKind.airbnb))
    ).scalar_one()
    assert ch.price_offset_pct is None  # sin persistir
    issues = (await session.execute(select(SyncIssue))).scalars().all()
    assert len(issues) == 1
    assert "airbnb" in (issues[0].entity_ref or "")
    assert (await session.execute(select(ChannelOffsetLog))).scalars().all() == []


async def test_apply_unverified_persists_but_flags_issue(session):
    # ok=True pero la relectura difiere (endpoint Alpha): se persiste el intento,
    # se marca verified=False y se abre incidencia para revisión.
    await _seed(session)
    cm = FakeCM(verified=False)
    result = await _preview_and_apply(session, cm, D("8"))
    assert result["applied"] and result["verified"] is False
    issues = (await session.execute(select(SyncIssue))).scalars().all()
    assert len(issues) == 1
