# Contract: agente — reservas y prompt multi-canal

**Feature**: 012-multichannel-core

## Tool `get_bookings` (extendida)

### Schema (entrada)

```json
{
  "type": "object",
  "properties": {
    "date_from": { "type": "string" },
    "date_to":   { "type": "string" },
    "channel":   { "type": "string", "enum": ["booking", "airbnb", "direct"] }
  },
  "required": ["date_from", "date_to"]
}
```

- `channel` opcional: filtra en SQL por `Booking.channel_kind`. Ausente ⇒ todos los canales.

### Salida (por reserva)

```json
{
  "external_ref": "76679573",
  "channel": "booking",
  "check_in": "2026-08-06",
  "check_out": "2026-08-19",
  "nights": 13
}
```

## System prompt (parametrizado)

```python
def system_prompt(today: date | None = None, active_channels: list[str] | None = None) -> str
```

- `active_channels` (p. ej. `["booking", "airbnb"]`) lo inyecta el orquestador desde
  los `Channel.is_active` de la BD; default `["booking"]` si no se pasa (retro-compatible
  para tests existentes que llaman `system_prompt()`).
- El texto resultante DEBE:
  1. Presentar al asistente como gestor de los canales activos (nombres legibles:
     "Booking.com y Airbnb"), no "solo el canal Booking".
  2. Indicar que los cambios de precio/disponibilidad/promoción se publican vía el
     Channel Manager a TODOS los canales conectados (FR-006).
  3. Indicar que `get_bookings` acepta filtro por canal y que las respuestas sobre
     reservas identifiquen el canal de cada una.
- El resto de reglas existentes (human-in-the-loop, promos vs deals con badge, etc.)
  se conservan tal cual.

## Criterios de aceptación

- "¿qué reservas tengo de Airbnb?" ⇒ una llamada a `get_bookings` con `channel="airbnb"`
  y respuesta solo con esas reservas (US2-AS1).
- Pregunta sin canal ⇒ respuesta con todas, cada una identificando su canal (US2-AS2).
- Propuesta de precio ⇒ el agente menciona que aplica a todos los canales conectados (US2-AS3).
