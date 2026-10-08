"""Textos FIJOS del asistente en el idioma del host (feature 021).

Las propuestas y resultados se generan en español (idioma de referencia, con montos
y fechas exactos) y aquí se traducen por plantillas antes de mostrarse. Lo que no
coincide con ninguna plantilla se devuelve tal cual (español). El texto libre del
LLM no pasa por aquí: lo controla la instrucción de idioma del system prompt.
"""

from __future__ import annotations

import re
from collections.abc import Callable

Lang = str  # "es" | "en" | "pt"

_CONFIRM = {"en": "Do you confirm?", "pt": "Você confirma?"}
_BIG = {"en": " ⚠️ This is a big change.", "pt": " ⚠️ É uma mudança grande."}

_EXACT: dict[str, dict[str, str]] = {
    "Entendido, cancelo la propuesta.": {
        "en": "Got it, I'm canceling the proposal.",
        "pt": "Entendido, cancelo a proposta.",
    },
    "No pude completar la solicitud.": {
        "en": "I couldn't complete the request.",
        "pt": "Não consegui concluir a solicitação.",
    },
    "No hay ninguna propuesta pendiente para confirmar.": {
        "en": "There's no pending proposal to confirm.",
        "pt": "Não há nenhuma proposta pendente para confirmar.",
    },
    "El estado cambió desde la propuesta; vuelvo a proponer.": {
        "en": "Things changed since the proposal; here's an updated one.",
        "pt": "O estado mudou desde a proposta; vou propor novamente.",
    },
    "No hay un LLM configurado. Configura OPENAI_API_KEY en .env para activar el agente.": {
        "en": "No LLM is configured. Set OPENAI_API_KEY to enable the assistant.",
        "pt": "Nenhum LLM configurado. Defina OPENAI_API_KEY para ativar o assistente.",
    },
    "Promoción eliminada.": {"en": "Promotion deleted.", "pt": "Promoção excluída."},
    "Promoción creada y publicada.": {"en": "Promotion created and published.", "pt": "Promoção criada e publicada."},
    "Promoción retirada (deja de aplicar el descuento).": {
        "en": "Promotion removed (the discount no longer applies).",
        "pt": "Promoção retirada (o desconto deixa de valer).",
    },
    "Cambio revertido y publicado.": {"en": "Change reverted and published.", "pt": "Alteração revertida e publicada."},
}

Fmt = Callable[[re.Match], str]


def _tail(m: re.Match, lang: Lang, group: str = "big") -> str:
    return (_BIG[lang] if m.group(group) else "") + " " + _CONFIRM[lang]


_PATTERNS: list[tuple[re.Pattern, dict[str, Fmt]]] = [
    (
        re.compile(
            r"^Propongo fijar (?P<price>\S+) COP en (?P<n>\d+) día\(s\)"
            r"(?: \((?P<inv>\d+) fuera de límites\))?\.(?P<big> ⚠️ Es un cambio grande\.)? ¿Confirmas\?$"
        ),
        {
            "en": lambda m: f"I propose setting {m['price']} COP on {m['n']} day(s)"
            + (f" ({m['inv']} outside price limits)" if m["inv"] else "")
            + "."
            + _tail(m, "en"),
            "pt": lambda m: f"Proponho definir {m['price']} COP em {m['n']} dia(s)"
            + (f" ({m['inv']} fora dos limites)" if m["inv"] else "")
            + "."
            + _tail(m, "pt"),
        },
    ),
    (
        re.compile(
            r"^Propongo (?P<verb>bloquear|abrir) (?P<n>\d+) noche\(s\)"
            r"(?: \((?P<sk>\d+) omitida\(s\)\))?\.(?P<big> ⚠️ Es un cambio grande\.)? ¿Confirmas\?$"
        ),
        {
            "en": lambda m: f"I propose {'blocking' if m['verb'] == 'bloquear' else 'opening'} {m['n']} night(s)"
            + (f" ({m['sk']} skipped)" if m["sk"] else "")
            + "."
            + _tail(m, "en"),
            "pt": lambda m: f"Proponho {'bloquear' if m['verb'] == 'bloquear' else 'abrir'} {m['n']} noite(s)"
            + (f" ({m['sk']} ignorada(s))" if m["sk"] else "")
            + "."
            + _tail(m, "pt"),
        },
    ),
    (
        re.compile(
            r"^Propongo (?P<verb>crear|editar) la promoción '(?P<name>.*)' \((?P<desc>.+?)\) del (?P<f>\S+) al (?P<l>\S+)"
            r"(?:, mínimo (?P<mn>\d+) noches)?(?: \(solo (?P<scope>[^)]+)\)| \(todos los canales\))\. ¿Confirmas\?$"
        ),
        {
            "en": lambda m: f"I propose {'creating' if m['verb'] == 'crear' else 'editing'} the promotion "
            f"'{m['name']}' ({_desc(m['desc'], 'en')}) from {m['f']} to {m['l']}"
            + (f", minimum {m['mn']} nights" if m["mn"] else "")
            + (f" (only {m['scope']})" if m["scope"] else " (all channels)")
            + ". Do you confirm?",
            "pt": lambda m: f"Proponho {'criar' if m['verb'] == 'crear' else 'editar'} a promoção "
            f"'{m['name']}' ({_desc(m['desc'], 'pt')}) de {m['f']} a {m['l']}"
            + (f", mínimo {m['mn']} noites" if m["mn"] else "")
            + (f" (apenas {m['scope']})" if m["scope"] else " (todos os canais)")
            + ". Você confirma?",
        },
    ),
    (
        re.compile(r"^Propongo crear la promoción '(?P<name>.*)' \((?P<v>\S+) (?P<t>\S+)\) del (?P<f>\S+) al (?P<l>\S+)\. ¿Confirmas\?$"),
        {
            "en": lambda m: f"I propose creating the promotion '{m['name']}' ({m['v']} {m['t']}) from {m['f']} to {m['l']}. Do you confirm?",
            "pt": lambda m: f"Proponho criar a promoção '{m['name']}' ({m['v']} {m['t']}) de {m['f']} a {m['l']}. Você confirma?",
        },
    ),
    (
        re.compile(r"^Propongo eliminar la promoción (?P<id>\S+)\. ¿Confirmas\?$"),
        {
            "en": lambda m: f"I propose deleting promotion {m['id']}. Do you confirm?",
            "pt": lambda m: f"Proponho excluir a promoção {m['id']}. Você confirma?",
        },
    ),
    (
        re.compile(r"^Propongo retirar la promoción (?P<id>\S+) \(dejará de aplicar el descuento\)\. ¿Confirmas\?$"),
        {
            "en": lambda m: f"I propose removing promotion {m['id']} (the discount will stop applying). Do you confirm?",
            "pt": lambda m: f"Proponho retirar a promoção {m['id']} (o desconto deixará de valer). Você confirma?",
        },
    ),
    (
        re.compile(r"^Propongo revertir el cambio (?P<id>\S+)\. ¿Confirmas\?$"),
        {
            "en": lambda m: f"I propose reverting change {m['id']}. Do you confirm?",
            "pt": lambda m: f"Proponho reverter a alteração {m['id']}. Você confirma?",
        },
    ),
    (
        re.compile(
            r"^Propongo ajustar el precio del canal (?P<ch>\S+) a (?P<pct>\S+)% "
            r"\(ej\.: base (?P<b>\S+) → (?P<e>\S+) COP\)\.(?P<extra>.*) ¿Confirmas\?$"
        ),
        {
            "en": lambda m: f"I propose setting the {m['ch']} channel price to {m['pct']}% "
            f"(e.g. base {m['b']} → {m['e']} COP).{m['extra']} Do you confirm?",
            "pt": lambda m: f"Proponho ajustar o preço do canal {m['ch']} para {m['pct']}% "
            f"(ex.: base {m['b']} → {m['e']} COP).{m['extra']} Você confirma?",
        },
    ),
    (
        re.compile(r"^Listo: apliqué (?P<n>\d+) día\(s\) y publiqué el precio efectivo\.$"),
        {
            "en": lambda m: f"Done: I applied {m['n']} day(s) and published the effective price.",
            "pt": lambda m: f"Pronto: apliquei {m['n']} dia(s) e publiquei o preço efetivo.",
        },
    ),
    (
        re.compile(
            r"^Listo: (?P<verb>bloqueé|reabrí) (?P<n>\d+) noche\(s\)(?: \((?P<sk>\d+) omitida\(s\)\))? "
            r"y publiqué la disponibilidad\.$"
        ),
        {
            "en": lambda m: f"Done: I {'blocked' if m['verb'] == 'bloqueé' else 'reopened'} {m['n']} night(s)"
            + (f" ({m['sk']} skipped)" if m["sk"] else "")
            + " and published the availability.",
            "pt": lambda m: f"Pronto: {'bloqueei' if m['verb'] == 'bloqueé' else 'reabri'} {m['n']} noite(s)"
            + (f" ({m['sk']} ignorada(s))" if m["sk"] else "")
            + " e publiquei a disponibilidade.",
        },
    ),
    (
        re.compile(r"^Promoción '(?P<name>.*)' creada y aplicada\.$"),
        {
            "en": lambda m: f"Promotion '{m['name']}' created and applied.",
            "pt": lambda m: f"Promoção '{m['name']}' criada e aplicada.",
        },
    ),
    (
        re.compile(r"^Promoción guardada, pero falló la publicación: (?P<issue>.*)$"),
        {
            "en": lambda m: f"Promotion saved, but publishing failed: {m['issue']}",
            "pt": lambda m: f"Promoção salva, mas a publicação falhou: {m['issue']}",
        },
    ),
    (
        re.compile(r"^Ajuste del canal (?P<ch>\S+) aplicado: (?P<pct>\S+)%\.(?P<rest>.*)$"),
        {
            "en": lambda m: f"{m['ch']} channel adjustment applied: {m['pct']}%."
            + m["rest"].replace("⚠️ No se pudo verificar en el Channel Manager:", "⚠️ Couldn't verify it in the Channel Manager:"),
            "pt": lambda m: f"Ajuste do canal {m['ch']} aplicado: {m['pct']}%."
            + m["rest"].replace("⚠️ No se pudo verificar en el Channel Manager:", "⚠️ Não foi possível verificar no Channel Manager:"),
        },
    ),
]


def _desc(desc: str, lang: Lang) -> str:
    m = re.match(r"^(\S+)% de descuento$", desc)
    if m:
        return f"{m[1]}% off" if lang == "en" else f"{m[1]}% de desconto"
    m = re.match(r"^precio (\S+)$", desc)
    if m:
        return f"price {m[1]}" if lang == "en" else f"preço {m[1]}"
    return desc


def translate(text: str, lang: Lang) -> str:
    """Traduce un texto fijo del asistente; sin plantilla conocida → español."""
    if not text or lang not in ("en", "pt"):
        return text
    exact = _EXACT.get(text)
    if exact:
        return exact[lang]
    for pattern, by_lang in _PATTERNS:
        m = pattern.match(text)
        if m:
            return by_lang[lang](m)
    return text
