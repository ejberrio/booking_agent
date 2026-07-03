# Contract: agente — offsets por canal

**Feature**: 013-channel-pricing

## Tool `get_channel_offsets` (lectura)

Schema: `{}` (sin parámetros). Salida:

```json
[
  { "channel": "booking", "offset_pct": null, "supported": false },
  { "channel": "airbnb",  "offset_pct": 8.0,  "supported": true  }
]
```

## Tool `propose_channel_offset` (escritura — solo propone)

Schema:

```json
{
  "type": "object",
  "properties": {
    "channel": { "type": "string", "enum": ["booking", "airbnb"] },
    "offset_pct": { "type": "number" }
  },
  "required": ["channel", "offset_pct"]
}
```

- `build_proposal` llama al preview del servicio (valida rango y soporte; canal no
  soportado → el agente explica la alternativa honesta).
- `apply_proposal` tras `confirm_pending` (patrón existente; el agente NUNCA aplica solo).

## Prompt (extensión)

- Nueva regla: "AJUSTE POR CANAL: consulta `get_channel_offsets` cuando el host pregunte
  por precios por canal. Si hay un ajuste ≠ 0, al proponer precios menciona el efecto por
  canal (p. ej. '300.000 en Booking, ~324.000 en Airbnb con tu +8%'). Para cambiar el
  ajuste usa `propose_channel_offset` (el host confirma). Booking vende al precio base
  (su ajuste no es configurable)."
- Se conservan todas las reglas existentes.

## Criterios de aceptación

- "ponle +8% a Airbnb" → `propose_channel_offset(channel=airbnb, offset_pct=8)` → propuesta
  con ejemplo → confirmación → aplicado y auditado (US1).
- "¿a cuánto queda la noche del 15 en cada canal?" → usa `get_calendar` + `get_channel_offsets`
  y responde por canal (US2-AS2).
- Propuesta de precio con offset activo menciona el efecto por canal (US2-AS3 / FR-006).
