"""Extracción de eventos desde resultados de búsqueda usando el LLM (inyectable).

Descarta candidatos sin fecha utilizable. En tests, un LLM falso devuelve el JSON
guionizado, sin llamar a la API real.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date

from app.core.config import settings
from app.models.enums import EventKind, Relevance
from app.search.base import SearchResult

_EXTRACT_PROMPT = (
    "Extrae eventos de Medellín de los siguientes resultados de búsqueda. "
    "Devuelve SOLO un array JSON; cada elemento: "
    '{"name","start_date":"YYYY-MM-DD","end_date":null,"kind":'
    '"concert|fair|convention|holiday|festival|other","relevance":"low|medium|high","location"}. '
    "Omite los que no tengan fecha clara."
)


@dataclass(frozen=True)
class EventCandidate:
    name: str
    start_date: date
    kind: EventKind
    relevance: Relevance
    end_date: date | None = None
    location: str | None = None


def _parse_date(value) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


async def extract_events(llm, results: list[SearchResult]) -> list[EventCandidate]:
    if not results:
        return []
    blob = "\n\n".join(f"{r.title}\n{r.content}" for r in results)
    resp = await llm.chat(
        messages=[
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": blob},
        ],
        tools=[],
        model=settings.llm_model,
    )
    # El LLM puede envolver el JSON en ```json ... ``` o añadir prosa; extraer el array.
    content = resp.content or "[]"
    match = re.search(r"\[.*\]", content, re.DOTALL)
    raw = match.group(0) if match else content
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []

    out: list[EventCandidate] = []
    for it in items if isinstance(items, list) else []:
        start = _parse_date(it.get("start_date"))
        if start is None:
            continue  # sin fecha utilizable -> descartar
        try:
            kind = EventKind(it.get("kind", "other"))
        except ValueError:
            kind = EventKind.other
        try:
            relevance = Relevance(it.get("relevance", "medium"))
        except ValueError:
            relevance = Relevance.medium
        out.append(
            EventCandidate(
                name=it.get("name", "Evento"),
                start_date=start,
                end_date=_parse_date(it.get("end_date")),
                kind=kind,
                relevance=relevance,
                location=it.get("location"),
            )
        )
    return out
