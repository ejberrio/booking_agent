"""Feature 019 · US3: agrupación PURA de sugerencias vendibles en bloques."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.suggestion_blocks import BlockInput, build_blocks

D = Decimal


@dataclass(frozen=True)
class N:
    date: date
    suggestion_id: int
    current_price: Decimal | None
    suggested_price: Decimal


def _ev(name):
    return [{"kind": "event", "label": f"{name} (high, +30%)", "event": {"name": name}}]


def _gap():
    return [{"kind": "gap", "label": "libre a 5 días (−9%)"}]


def _inp(sid, days, factors, cur="300000", sug="390000"):
    return BlockInput(
        suggestion_id=sid,
        nights=[N(date(2026, 12, d), sid, D(cur), D(sug)) for d in days],
        factors=factors,
    )


def test_mismo_evento_no_contiguo_un_bloque():
    blocks = build_blocks([_inp(1, [1], _ev("Martin Garrix")), _inp(2, [5], _ev("Martin Garrix"))])
    assert len(blocks) == 1
    b = blocks[0]
    assert b.kind == "event" and b.title == "Martin Garrix"
    assert (b.date_from, b.date_to) == (date(2026, 12, 1), date(2026, 12, 5))
    assert b.suggestion_ids == [1, 2]


def test_nombre_de_evento_normalizado():
    blocks = build_blocks([_inp(1, [1], _ev("Beéle Tour")), _inp(2, [2], _ev("beele  tour"))])
    assert len(blocks) == 1


def test_huecos_contiguos_un_bloque_y_corte():
    blocks = build_blocks(
        [
            _inp(1, [20], _gap(), sug="250000"),
            _inp(2, [21], _gap(), sug="252000"),
            _inp(3, [23], _gap(), sug="255000"),  # 22 sin sugerencia → corte
        ]
    )
    assert [(b.kind, b.title, len(b.nights)) for b in blocks] == [
        ("period", "Libre próximo", 2),
        ("period", "Libre próximo", 1),
    ]


def test_evento_y_periodo_no_se_mezclan():
    blocks = build_blocks([_inp(1, [10], _ev("Feria")), _inp(2, [11], _gap(), sug="250000")])
    assert {b.kind for b in blocks} == {"event", "period"}
    assert len(blocks) == 2


def test_v1_sin_factors_es_otras():
    blocks = build_blocks([_inp(1, [3, 4], [])])
    assert blocks[0].title == "Otras" and blocks[0].kind == "period"


def test_direction_y_bajadas_presentes():
    up = build_blocks([_inp(1, [1], _ev("A"), sug="390000")])[0]
    down = build_blocks([_inp(2, [2], _gap(), sug="250000")])[0]
    mixed = build_blocks([_inp(3, [3], _ev("B"), sug="390000"), _inp(4, [4], _ev("B"), sug="250000")])[0]
    assert (up.direction, down.direction, mixed.direction) == ("up", "down", "mixed")


def test_sin_noches_no_genera_bloque_y_orden_por_fecha():
    blocks = build_blocks([_inp(1, [], _ev("X")), _inp(2, [9], _gap(), sug="1"), _inp(3, [2], _ev("Y"))])
    assert [b.title for b in blocks] == ["Y", "Libre próximo"]
