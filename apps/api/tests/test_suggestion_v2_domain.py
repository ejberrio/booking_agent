"""Feature 018: heurística v2 pura — señales simétricas, límites y desglose."""

from datetime import date
from decimal import Decimal

from app.domain.suggestion import EventSignal, suggest_price_v2
from app.market.provider import MarketSnapshot
from app.models.enums import Relevance

D = Decimal
MONTH = date(2026, 9, 1)


def _event(rel=Relevance.high, name="Concierto inaugural", location="Daviarena"):
    return EventSignal(
        relevance=rel, name=name, location=location, dates="2026-09-12",
        source_url="https://ejemplo.com/evento",
    )


def _snapshot(adr, samples=5):
    return MarketSnapshot(
        zone="Sabaneta", month=MONTH, adr=D(adr), occupancy_pct=None,
        sample_size=samples, source="tavily",
    )


def test_evento_sube_con_desglose():
    out = suggest_price_v2(D("300000"), event=_event())
    assert out.price == D("390000")  # +30%
    ev = next(f for f in out.factors if f.kind == "event")
    assert ev.event["name"] == "Concierto inaugural"
    assert ev.event["location"] == "Daviarena"
    assert ev.event["source_url"] == "https://ejemplo.com/evento"
    assert "Concierto inaugural" in out.text


def test_evento_mas_ocupacion():
    out = suggest_price_v2(D("100000"), event=_event(Relevance.medium), occupancy_high=True)
    assert out.price == D("125000")  # +15% +10%
    assert {f.kind for f in out.factors} == {"event", "occupancy"}


def test_hueco_progresivo_y_tope():
    # Más cerca ⇒ mayor descuento; tope −15%
    p14 = suggest_price_v2(D("100000"), gap_days_ahead=14).price
    p9 = suggest_price_v2(D("100000"), gap_days_ahead=9).price
    p3 = suggest_price_v2(D("100000"), gap_days_ahead=3).price
    p0 = suggest_price_v2(D("100000"), gap_days_ahead=0).price
    assert p14 > p9 > p3 >= p0
    assert p0 == D("85000")  # tope −15%
    gap = next(f for f in suggest_price_v2(D("100000"), gap_days_ahead=9).factors if f.kind == "gap")
    assert gap.pct < 0


def test_piso_min_price_gana_al_descuento():
    out = suggest_price_v2(D("100000"), gap_days_ahead=0, min_price=D("95000"))
    assert out.price == D("95000")


def test_techo_max_price():
    out = suggest_price_v2(D("100000"), event=_event(), occupancy_high=True, max_price=D("110000"))
    assert out.price == D("110000")


def test_mercado_ancla_con_muestras():
    out = suggest_price_v2(D("300000"), event=_event(Relevance.medium), market=_snapshot("310000"))
    # +15% = 345000; con evento el mercado pesa 25%: 0,75·345000 + 0,25·310000 = 336250
    assert out.price == D("336250")
    assert any(f.kind == "market" and "pesa 25%" in f.label for f in out.factors)
    assert any(f.kind == "market" and "5 tarifas" in f.label for f in out.factors)


def test_mercado_pocas_muestras_no_ancla():
    out = suggest_price_v2(
        D("300000"), event=_event(Relevance.medium), market=_snapshot("310000", samples=2)
    )
    assert out.price == D("345000")  # sin ancla
    assert any(f.kind == "market" and "confianza baja" in f.label for f in out.factors)


def test_sin_mercado_sin_factor_market():
    out = suggest_price_v2(D("300000"), event=_event())
    assert all(f.kind != "market" for f in out.factors)


def test_mercado_solo_no_dispara():
    assert suggest_price_v2(D("300000"), market=_snapshot("250000")) is None


def test_sin_senales_none():
    assert suggest_price_v2(D("300000")) is None


def test_confidence_por_senales():
    one = suggest_price_v2(D("100000"), event=_event())
    two = suggest_price_v2(D("100000"), event=_event(), occupancy_high=True)
    assert two.confidence > one.confidence


def test_mercado_no_comparable_se_descarta_y_no_hunde_el_evento():
    # Caso real (oct 2026): evento +30% sobre 270.000 con "mercado" ~52.000 (habitaciones/USD).
    out = suggest_price_v2(D("270000"), event=_event(), market=_snapshot("52000"))
    assert out.price == D("351000")  # +30% intacto, sin ancla absurda
    assert any(f.kind == "market" and "descartado" in f.label for f in out.factors)
    assert out.confidence == D("0.5")  # el mercado descartado no suma confianza


def test_mercado_mas_barato_pero_creible_si_baja_el_precio():
    # Competencia de verdad más barata: el ancla debe poder bajar (no solo subir).
    out = suggest_price_v2(D("300000"), gap_days_ahead=10, market=_snapshot("220000"))
    assert out.price < D("300000")
    assert any(f.kind == "market" and "tarifas" in f.label for f in out.factors)


def test_mercado_demasiado_caro_tambien_se_descarta():
    out = suggest_price_v2(D("300000"), event=_event(Relevance.medium), market=_snapshot("900000"))
    assert out.price == D("345000")
    assert any(f.kind == "market" and "descartado" in f.label for f in out.factors)


def test_sin_evento_el_mercado_pesa_50():
    # hueco a 10 días (−7%): 300000 → 279000; ancla 50/50 con 250000 = 264500
    out = suggest_price_v2(D("300000"), gap_days_ahead=10, market=_snapshot("250000"))
    assert out.price == D("264500")
    assert any(f.kind == "market" and "pesa 50%" in f.label for f in out.factors)


def test_evento_fuerte_con_mercado_barato_caso_chayanne():
    # Caso real (nov 2026): tarifa 370000, evento +30% (481000), mercado 192000.
    # Antes (50/50) bajaba a 336500; con 25% sube a 0,75·481000 + 0,25·192000 = 408750.
    out = suggest_price_v2(D("370000"), event=_event(), market=_snapshot("192000"))
    assert out.price == D("408750")


def test_factores_estructurados_para_traducir():
    out = suggest_price_v2(D("300000"), event=_event(Relevance.medium), market=_snapshot("310000"))
    ev = next(f for f in out.factors if f.kind == "event")
    mk = next(f for f in out.factors if f.kind == "market")
    assert ev.data == {"relevance": "medium"}
    assert mk.data == {"adr": "310000", "samples": 5, "source": "tavily", "state": "used", "weight": 0.25}
    gap = suggest_price_v2(D("300000"), gap_days_ahead=10).factors[0]
    assert gap.data == {"days": 10}
    disc = suggest_price_v2(D("270000"), event=_event(), market=_snapshot("52000"))
    assert next(f for f in disc.factors if f.kind == "market").data["state"] == "discarded"
    low = suggest_price_v2(D("300000"), event=_event(), market=_snapshot("310000", samples=2))
    assert next(f for f in low.factors if f.kind == "market").data["state"] == "low_confidence"
