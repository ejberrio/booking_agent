"""Feature 023: dominio puro de la extensión de precios."""

from datetime import date, timedelta
from decimal import Decimal as D

from app.domain.price_extension import night_price, propose_template, round_1000


def _span(first: date, n: int, price: str) -> dict[date, D]:
    return {first + timedelta(days=i): D(price) for i in range(n)}


def test_redondeo_a_miles():
    assert round_1000(D("377500")) == D("378000")
    assert round_1000(D("377499")) == D("377000")


def test_mediana_del_mismo_mes_sin_eventos():
    known = _span(date(2026, 11, 1), 30, "370000")
    event = {date(2026, 11, 14) + timedelta(days=i) for i in range(5)}
    known.update({d: D("611000") for d in event})
    t = propose_template(known, event, ["2027-11"])
    assert t == {"2027-11": D("370000")}


def test_eventos_cuentan_si_no_se_excluyen():
    known = _span(date(2026, 11, 1), 4, "300000") | _span(date(2026, 11, 5), 6, "600000")
    assert propose_template(known, set(), ["2027-11"])["2027-11"] == D("600000")


def test_mes_sin_datos_usa_mediana_global_y_meses_de_dos_anos_son_distintos():
    known = _span(date(2026, 12, 1), 31, "378000") | _span(date(2026, 10, 1), 31, "270000") | _span(
        date(2027, 1, 1), 31, "378000"
    )
    t = propose_template(known, set(), ["2027-02", "2027-12", "2028-02"])
    assert t["2027-02"] == D("378000")  # mediana global
    assert t["2027-12"] == D("378000")
    assert set(t) == {"2027-02", "2027-12", "2028-02"}


def test_sin_datos_usa_fallback():
    assert propose_template({}, set(), ["2027-03"], fallback=D("230000")) == {"2027-03": D("230000")}
    assert propose_template({}, set(), ["2027-03"]) == {"2027-03": None}
    # precios 0 no cuentan como datos
    assert propose_template({date(2027, 3, 1): D("0")}, set(), ["2027-03"]) == {"2027-03": None}


def test_fin_de_semana_y_limites():
    fri, tue = date(2027, 3, 5), date(2027, 3, 2)
    assert night_price(D("350000"), fri, D("10"), None, None) == (D("385000"), None)
    assert night_price(D("350000"), tue, D("10"), None, None) == (D("350000"), None)
    assert night_price(D("200000"), tue, D("0"), D("230000"), None) == (D("230000"), "min")
    assert night_price(D("400000"), fri, D("10"), None, D("420000")) == (D("420000"), "max")


def test_mes_casi_todo_con_eventos_usa_todas_sus_noches():
    # julio cubierto por una feria larga: sin noches limpias suficientes → mediana de todo julio
    known = _span(date(2026, 7, 1), 31, "350000") | _span(date(2026, 12, 1), 31, "378000")
    feria = {date(2026, 7, 1) + timedelta(days=i) for i in range(28)}
    t = propose_template(known, feria, ["2027-07", "2027-03"])
    assert t["2027-07"] == D("350000")
    # la mediana global usa las noches limpias (3 de julio + 31 de diciembre)
    assert t["2027-03"] == D("378000")
