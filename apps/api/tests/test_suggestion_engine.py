from decimal import Decimal

from app.domain.suggestion import suggest_price
from app.models.enums import Relevance

D = Decimal


def test_high_event_high_occupancy_raises():
    out = suggest_price(
        D("100000"), event_relevance=Relevance.high, occupancy_high=True,
        market_ref=None, min_price=None, max_price=None,
    )
    assert out is not None
    assert out.price > D("100000")
    assert "evento" in out.justification


def test_low_event_small_uplift():
    out = suggest_price(
        D("100000"), event_relevance=Relevance.low, occupancy_high=False,
        market_ref=None, min_price=None, max_price=None,
    )
    assert out.price == D("105000")  # +5%


def test_clamped_to_limits():
    out = suggest_price(
        D("100000"), event_relevance=Relevance.high, occupancy_high=True,
        market_ref=None, min_price=None, max_price=D("110000"),
    )
    assert out.price == D("110000")  # acotado al máximo


def test_no_signal_returns_none():
    assert (
        suggest_price(
            D("100000"), event_relevance=None, occupancy_high=False,
            market_ref=None, min_price=None, max_price=None,
        )
        is None
    )


def test_market_only_blends_toward_reference():
    out = suggest_price(
        D("100000"), event_relevance=None, occupancy_high=False,
        market_ref=D("140000"), min_price=None, max_price=None,
    )
    assert out is not None
    assert out.price == D("120000")  # (100000 + 140000) / 2
