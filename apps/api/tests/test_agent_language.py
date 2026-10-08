"""Feature 021: el asistente responde en el idioma del host (prompt + textos fijos)."""

from datetime import date

import httpx
import pytest

from app.agent import texts
from app.agent.prompts import system_prompt
from app.main import app

TODAY = date(2026, 10, 8)


def test_prompt_incluye_instruccion_de_idioma():
    assert "responde SIEMPRE en español" in system_prompt(TODAY)  # por defecto
    assert "responde SIEMPRE en inglés (English" in system_prompt(TODAY, language="en")
    assert "portugués de Brasil" in system_prompt(TODAY, language="pt")
    # la instrucción va al final para que prime sobre lo anterior
    assert system_prompt(TODAY, language="en").rstrip().endswith("canales).")
    assert "en español." not in system_prompt(TODAY, language="en")


@pytest.mark.parametrize(
    ("es", "en", "pt"),
    [
        (
            "Propongo fijar 312500 COP en 5 día(s). ¿Confirmas?",
            "I propose setting 312500 COP on 5 day(s). Do you confirm?",
            "Proponho definir 312500 COP em 5 dia(s). Você confirma?",
        ),
        (
            "Propongo fijar 900000 COP en 20 día(s) (2 fuera de límites). ⚠️ Es un cambio grande. ¿Confirmas?",
            "I propose setting 900000 COP on 20 day(s) (2 outside price limits). ⚠️ This is a big change. Do you confirm?",
            "Proponho definir 900000 COP em 20 dia(s) (2 fora dos limites). ⚠️ É uma mudança grande. Você confirma?",
        ),
        (
            "Propongo bloquear 13 noche(s) (1 omitida(s)). ¿Confirmas?",
            "I propose blocking 13 night(s) (1 skipped). Do you confirm?",
            "Proponho bloquear 13 noite(s) (1 ignorada(s)). Você confirma?",
        ),
        (
            "Propongo crear la promoción 'Visibilidad Julio' (20% de descuento) del 2026-07-07 al 2026-07-31, mínimo 2 noches (solo airbnb). ¿Confirmas?",
            "I propose creating the promotion 'Visibilidad Julio' (20% off) from 2026-07-07 to 2026-07-31, minimum 2 nights (only airbnb). Do you confirm?",
            "Proponho criar a promoção 'Visibilidad Julio' (20% de desconto) de 2026-07-07 a 2026-07-31, mínimo 2 noites (apenas airbnb). Você confirma?",
        ),
        (
            "Listo: apliqué 3 día(s) y publiqué el precio efectivo.",
            "Done: I applied 3 day(s) and published the effective price.",
            "Pronto: apliquei 3 dia(s) e publiquei o preço efetivo.",
        ),
        (
            "Listo: reabrí 2 noche(s) y publiqué la disponibilidad.",
            "Done: I reopened 2 night(s) and published the availability.",
            "Pronto: reabri 2 noite(s) e publiquei a disponibilidade.",
        ),
        (
            "Entendido, cancelo la propuesta.",
            "Got it, I'm canceling the proposal.",
            "Entendido, cancelo a proposta.",
        ),
    ],
)
def test_textos_fijos_traducidos_conservan_montos_y_nombres(es, en, pt):
    assert texts.translate(es, "es") == es
    assert texts.translate(es, "en") == en
    assert texts.translate(es, "pt") == pt


def test_texto_desconocido_queda_en_espanol():
    libre = "Texto libre del modelo que no es plantilla"
    assert texts.translate(libre, "en") == libre


@pytest.mark.anyio
async def test_chat_rechaza_idioma_no_soportado():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/chat", json={"message": "hola", "language": "fr"})
    assert r.status_code == 422
