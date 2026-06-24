from datetime import date
from decimal import Decimal

from app.domain.pricing import PromotionLike, best_promotion, effective_price, violates_rule
from app.models.enums import PromotionType

D = Decimal
DAY = date(2026, 7, 15)


def _percent(value: str, start: date, end: date) -> PromotionLike:
    return PromotionLike(PromotionType.percent, D(value), start, end)


def test_effective_no_promo():
    assert effective_price(D("100.00"), [], DAY) == D("100.00")


def test_overlapping_promos_takes_max():
    p10 = _percent("10", date(2026, 7, 1), date(2026, 7, 31))
    p20 = _percent("20", date(2026, 7, 10), date(2026, 7, 20))
    # Gana la de mayor descuento (20%), NO se acumulan (no 30%).
    assert effective_price(D("100.00"), [p10, p20], DAY) == D("80.00")
    assert best_promotion([p10, p20], D("100.00"), DAY) is p20


def test_amount_promo():
    pa = PromotionLike(PromotionType.amount, D("30"), date(2026, 7, 1), date(2026, 7, 31))
    assert effective_price(D("100.00"), [pa], DAY) == D("70.00")


def test_promo_not_covering_day():
    p = _percent("50", date(2026, 8, 1), date(2026, 8, 5))
    assert effective_price(D("100.00"), [p], DAY) == D("100.00")


def test_effective_never_below_zero():
    pa = PromotionLike(PromotionType.amount, D("500"), date(2026, 7, 1), date(2026, 7, 31))
    assert effective_price(D("100.00"), [pa], DAY) == D("0.00")


def test_violates_rule():
    assert violates_rule(D("50"), D("80"), D("200")) is True
    assert violates_rule(D("250"), D("80"), D("200")) is True
    assert violates_rule(D("100"), D("80"), D("200")) is False
    assert violates_rule(D("100"), None, None) is False
