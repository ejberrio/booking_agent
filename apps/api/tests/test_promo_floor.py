"""Feature 022: precio de la promoción con precio mínimo y descuentos acumulables."""

from decimal import Decimal as D

from app.domain.promo_floor import SKIP_BELOW_MIN, SKIP_TOO_SMALL, plan_promo

MOBILE = {"booking": D("10"), "airbnb": D("10")}


def test_sin_minimo_usa_el_sugerido():
    p = plan_promo(D("270000"), D("240300"), None, MOBILE)
    assert (p.price, p.pct, p.clipped) == (D("240300"), D("11.0"), False)
    assert p.final_by_channel == {"booking": D("216270"), "airbnb": D("216270")}


def test_caso_del_spec_recorta_por_el_movil():
    # base 270.000, sugerido −15 % (229.500), mínimo 230.000, móvil 10 %:
    # desde el celular debe quedar ≥ 230.000 → precio ≥ 255.556 (≈ −5,3 %).
    p = plan_promo(D("270000"), D("229500"), D("230000"), MOBILE)
    assert p.clipped is True and p.price == D("255556")
    assert all(v >= D("230000") for v in p.final_by_channel.values())
    assert p.pct == D("5.3")


def test_manda_el_canal_mas_exigente():
    p = plan_promo(D("300000"), D("240000"), D("200000"), {"booking": D("0"), "airbnb": D("20")})
    assert p.price == D("250000")  # 200.000 / 0,8
    assert p.final_by_channel == {"booking": D("250000"), "airbnb": D("200000")}


def test_minimo_mayor_o_igual_al_base_omite():
    p = plan_promo(D("230000"), D("200000"), D("230000"), MOBILE)
    assert p.price is None and p.skip_reason == SKIP_BELOW_MIN


def test_recorte_que_deja_menos_de_1_pct_omite_por_minimo():
    p = plan_promo(D("260000"), D("230000"), D("235000"), MOBILE)  # piso 261.112 > base
    assert p.price is None and p.skip_reason == SKIP_BELOW_MIN


def test_bajada_menor_a_1_pct_omite():
    p = plan_promo(D("270000"), D("268000"), None, MOBILE)
    assert p.price is None and p.skip_reason == SKIP_TOO_SMALL


def test_sugerido_por_encima_del_piso_no_recorta():
    p = plan_promo(D("400000"), D("340000"), D("230000"), MOBILE)
    assert (p.price, p.clipped) == (D("340000"), False)
