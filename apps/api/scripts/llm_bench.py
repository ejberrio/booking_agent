"""Comparación mínima de modelos de OpenAI para las tareas reales de StayLever.

Se ejecuta DENTRO del servidor de pruebas (la clave nunca sale de allí):
    railway ssh --service api-staging --environment staging -- python -m scripts.llm_bench

Tareas: extraer eventos, extraer precios de mercado y las llamadas a herramientas del agente
(consultar precio y proponer un cambio). Imprime aciertos, latencia, tokens y costo estimado.
No escribe en la base ni en ningún canal.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time

import litellm

from app.agent.prompts import system_prompt
from app.agent.tools import openai_tools

PRICES = {  # USD por 1M tokens (entrada, salida) — precios públicos de OpenAI, oct-2026
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-6-luna": (0.10, 0.50),
}
CANDIDATES = [
    ("gpt-4o-mini", None),
    ("gpt-4o", None),
    ("gpt-5.6-luna", "none"),
    ("gpt-6-luna", "none"),
]
REPS = 2

EVENTS_PROMPT = (
    "Extrae eventos de Medellín de los siguientes resultados de búsqueda. "
    "Devuelve SOLO un array JSON; cada elemento: "
    '{"name","start_date":"YYYY-MM-DD","end_date":null,"kind":'
    '"concert|fair|convention|holiday|festival|other","relevance":"low|medium|high","location"}. '
    "Omite los que no tengan fecha clara."
)
EVENTS_TEXT = """Agenda Medellín noviembre 2026
Karol G regresa al Atanasio Girardot el 14 y 15 de noviembre de 2026 con dos conciertos.
Colombiamoda 2027 se celebrará del 27 al 29 de julio de 2027 en Plaza Mayor.
La Feria de las Flores 2027 tendrá su desfile de silleteros el 8 de agosto de 2027.
Próximamente: gran festival gastronómico (fecha por confirmar).
Expo Inmobiliaria Medellín, 5 al 7 de marzo de 2027, Plaza Mayor."""
EVENTS_EXPECTED = {"2026-11-14", "2027-07-27", "2027-08-08", "2027-03-05"}

MARKET_PROMPT = (
    "De los siguientes resultados de búsqueda, extrae PRECIOS POR NOCHE en COP de "
    "APARTAMENTOS COMPLETOS de la zona indicada. Devuelve SOLO un array JSON de "
    "números (COP por noche, sin separadores). Omite habitaciones privadas, camas en "
    "hostal, precios por mes, por persona, en USD u otra moneda, o claramente de otra "
    "zona. Si no hay precios claros: []."
)
MARKET_TEXT = """Zona: Sabaneta, Antioquia. Mes: noviembre 2026.
Apartamento completo 3 habitaciones con piscina en Sabaneta: $350.000 COP por noche.
Habitación privada en Sabaneta: $90.000 COP la noche.
Apartamento amoblado Sabaneta arriendo mensual $4.500.000.
Loft completo cerca a Mayorca, Sabaneta, desde 420.000 COP/noche.
Apartamento en El Poblado USD 120 por noche."""
MARKET_EXPECTED = {350000, 420000}

UNITS = (
    "\n- El host tiene UNA sola unidad: unit_type_id=1 «3BR», property_id=1 "
    "(«Apto piscina», Sabaneta, moneda COP). Usa esos identificadores en todas las "
    "herramientas SIN preguntar al host por IDs."
)


def _cost(model, usage) -> float:
    pin, pout = PRICES[model]
    return (usage.prompt_tokens * pin + usage.completion_tokens * pout) / 1_000_000


async def _call(model, effort, messages, tools=None):
    kwargs = {"model": f"openai/{model}", "messages": messages,
              "api_key": os.environ["OPENAI_API_KEY"]}
    if effort:
        kwargs["reasoning_effort"] = effort
        # LiteLLM aún no conoce los modelos más nuevos: se le permite pasar el parámetro.
        kwargs["allowed_openai_params"] = ["reasoning_effort"]
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    t0 = time.perf_counter()
    resp = await litellm.acompletion(**kwargs)
    return resp, time.perf_counter() - t0


def _json_array(text):
    m = re.search(r"\[.*\]", text or "", re.DOTALL)
    try:
        return json.loads(m.group(0) if m else "[]")
    except json.JSONDecodeError:
        return []


async def task_events(model, effort):
    resp, dt = await _call(model, effort, [
        {"role": "system", "content": EVENTS_PROMPT}, {"role": "user", "content": EVENTS_TEXT}])
    got = {e.get("start_date") for e in _json_array(resp.choices[0].message.content)
           if isinstance(e, dict)}
    found = len(got & EVENTS_EXPECTED)
    ok = found == len(EVENTS_EXPECTED) and not (got - EVENTS_EXPECTED)
    return ok, dt, resp.usage, f"{found}/4 eventos · fechas={sorted(d for d in got if d)}"


async def task_market(model, effort):
    resp, dt = await _call(model, effort, [
        {"role": "system", "content": MARKET_PROMPT}, {"role": "user", "content": MARKET_TEXT}])
    got = {int(float(x)) for x in _json_array(resp.choices[0].message.content)
           if isinstance(x, (int, float, str)) and str(x).replace(".", "").isdigit()}
    return got == MARKET_EXPECTED, dt, resp.usage, f"precios={sorted(got)}"


def _agent_messages(text):
    return [{"role": "system", "content": system_prompt(active_channels=["booking", "airbnb"])
             + UNITS}, {"role": "user", "content": text}]


async def task_read(model, effort):
    resp, dt = await _call(model, effort, _agent_messages(
        "¿Qué precio tengo el 20 de noviembre?"), openai_tools(include_control=False))
    calls = resp.choices[0].message.tool_calls or []
    c = calls[0] if calls else None
    args = json.loads(c.function.arguments) if c else {}
    ok = bool(c) and c.function.name == "get_calendar" and int(args.get("unit_type_id", 0)) == 1 \
        and args.get("date_from", "") <= "2026-11-20" <= args.get("date_to", "")
    return ok, dt, resp.usage, f"{c.function.name if c else 'sin llamada'} {args}"


FAKE_READS = {
    "get_channel_offsets": [{"channel": "booking", "offset_pct": "0"},
                            {"channel": "airbnb", "offset_pct": "0"}],
    "get_calendar": [{"date": "2026-11-20", "base_price": 350000, "available": 1}],
}


class _Usage:
    def __init__(self):
        self.prompt_tokens = self.completion_tokens = 0


async def task_write(model, effort):
    """Hasta 3 pasos: puede consultar antes (lecturas simuladas) y luego debe proponer."""
    messages = _agent_messages("Pon el precio del 20 de noviembre en 400000")
    usage, dt, c, args = _Usage(), 0.0, None, {}
    for _ in range(3):
        resp, step = await _call(model, effort, messages, openai_tools(include_control=False))
        dt += step
        usage.prompt_tokens += resp.usage.prompt_tokens
        usage.completion_tokens += resp.usage.completion_tokens
        calls = resp.choices[0].message.tool_calls or []
        c = calls[0] if calls else None
        args = json.loads(c.function.arguments) if c else {}
        if not c or c.function.name.startswith("propose_"):
            break
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}]})
        messages.append({"role": "tool", "tool_call_id": c.id,
                         "content": json.dumps(FAKE_READS.get(c.function.name, []))})
    day_ok = args.get("day") == "2026-11-20" or (
        args.get("date_from") == "2026-11-20" and args.get("date_to") == "2026-11-20")
    ok = bool(c) and c.function.name in ("propose_set_day", "propose_set_range") \
        and int(args.get("unit_type_id", 0)) == 1 and float(args.get("price", 0)) == 400000 \
        and day_ok
    return ok, dt, usage, f"{c.function.name if c else 'sin llamada'} {args}"


TASKS = [("eventos", task_events), ("mercado", task_market),
         ("agente: consulta", task_read), ("agente: cambio", task_write)]


async def main():
    litellm.suppress_debug_info = True
    for model, effort in CANDIDATES:
        print(f"\n=== {model} (reasoning_effort={effort}) ===")
        total_cost = total_time = 0.0
        hits = runs = 0
        for name, fn in TASKS:
            for _ in range(REPS):
                try:
                    ok, dt, usage, detail = await fn(model, effort)
                except Exception as exc:  # noqa: BLE001 — solo tipo y mensaje corto
                    print(f"  {name}: ERROR {type(exc).__name__}: {str(exc)[:160]}")
                    runs += 1
                    continue
                cost = _cost(model, usage)
                total_cost += cost
                total_time += dt
                hits += ok
                runs += 1
                print(f"  {name}: {'OK ' if ok else 'MAL'} {dt:5.1f}s "
                      f"in={usage.prompt_tokens} out={usage.completion_tokens} "
                      f"${cost:.5f}  {detail}")
        print(f"  TOTAL {hits}/{runs} aciertos · {total_time:.1f}s · ${total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
