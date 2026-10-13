"""Feature 013 · US2: tools y prompt del agente para offsets por canal (T011)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.agent.prompts import system_prompt
from app.agent.tools import READ_TOOLS, WRITE_TOOLS, apply_proposal, build_proposal, exec_read
from app.models.enums import ChannelKind
from app.models.property import Channel, Property, UnitType
from tests.test_channel_pricing_service import FakeCM

TODAY = date(2026, 7, 15)


async def _seed(session, *, offset=None):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    session.add(
        Channel(
            property_id=prop.id, kind=ChannelKind.airbnb, is_active=True, price_offset_pct=offset
        )
    )
    await session.flush()


# --- tool de lectura -----------------------------------------------------------


def test_get_channel_offsets_declared_as_read_tool():
    spec = next(t for t in READ_TOOLS if t.name == "get_channel_offsets")
    assert spec.is_write is False


async def test_get_channel_offsets_output(session, monkeypatch):
    import app.agent.tools as tools_mod

    await _seed(session, offset=D("8"))
    monkeypatch.setattr(tools_mod, "get_adapter", lambda *_a, **_k: _closable(FakeCM()))
    out = await exec_read(session, "get_channel_offsets", {})
    by = {o["channel"]: o for o in out}
    assert by["airbnb"]["offset_pct"] == 8.0
    assert by["airbnb"]["supported"] is True
    assert by["booking"]["supported"] is False


# --- tool de propuesta (escritura con confirmación) -----------------------------


def test_propose_channel_offset_declared_as_write_tool():
    spec = next(t for t in WRITE_TOOLS if t.name == "propose_channel_offset")
    assert spec.is_write is True
    assert spec.parameters["properties"]["channel"]["enum"] == ["booking", "airbnb"]


@pytest.fixture()
def fake_adapter(monkeypatch):
    import app.agent.tools as tools_mod

    monkeypatch.setattr(tools_mod, "get_adapter", lambda *_a, **_k: _closable(FakeCM()))
    return None


def _closable(cm):
    async def _noop():
        return None

    cm.aclose = _noop
    return cm


async def test_propose_builds_preview_without_applying(session, fake_adapter):
    await _seed(session)
    proposal = await build_proposal(
        session, "propose_channel_offset", {"channel": "airbnb", "offset_pct": 8}
    )
    assert "8" in proposal.summary and "airbnb" in proposal.summary.lower()
    # NO aplicó nada:
    ch = (
        await session.execute(select(Channel).where(Channel.kind == ChannelKind.airbnb))
    ).scalar_one()
    assert ch.price_offset_pct is None


async def test_propose_unsupported_channel_raises_honest_error(session, fake_adapter):
    await _seed(session)
    with pytest.raises(ValueError) as exc:
        await build_proposal(
            session, "propose_channel_offset", {"channel": "booking", "offset_pct": 5}
        )
    assert "precio base" in str(exc.value)


async def test_apply_proposal_applies_offset(session):
    from types import SimpleNamespace

    await _seed(session)
    cm = FakeCM()
    action = SimpleNamespace(
        tool="propose_channel_offset", arguments={"channel": "airbnb", "offset_pct": 8}
    )
    outcome = await apply_proposal(session, cm, action, None)
    assert outcome.status == "applied"
    ch = (
        await session.execute(select(Channel).where(Channel.kind == ChannelKind.airbnb))
    ).scalar_one()
    assert ch.price_offset_pct == D("8")


# --- prompt ---------------------------------------------------------------------


def test_prompt_has_channel_offset_rule():
    p = system_prompt(TODAY, active_channels=["booking", "airbnb"])
    assert "get_channel_offsets" in p
    assert "propose_channel_offset" in p
    assert "efecto por canal" in p.lower()


def test_prompt_keeps_previous_rules():
    p = system_prompt(TODAY, active_channels=["booking", "airbnb"])
    assert "propose_offer_promotion" in p
    assert "TODOS los canales conectados" in p
    assert "HOY es" in p
