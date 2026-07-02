# Contract: GET /status — bloque `channels`

**Feature**: 012-multichannel-core

## Respuesta (extendida; campos existentes intactos)

```json
{
  "version": "0.1.2",
  "environment": "production",
  "db": "up",
  "beds24": "connected",
  "open_issues": 0,
  "channels": [
    { "kind": "booking", "is_active": true,  "bookings": 12 },
    { "kind": "airbnb",  "is_active": true,  "bookings": 3  },
    { "kind": "direct",  "is_active": false, "bookings": 1  }
  ]
}
```

## Reglas

- `channels` sale de la BD: filas de `Channel` de la propiedad + conteo de `Booking`
  confirmadas por `channel_kind`. Se incluye un kind sin fila `Channel` solo si tiene
  reservas (aparece con `is_active: false`).
- Patrón de resiliencia del endpoint: el cálculo va en su propio try/except con
  timeout; si falla ⇒ `"channels": []` y el endpoint responde igual (nunca 500).
- Orden estable: booking, airbnb, direct.
- Consumidor web: `GET /api/proxy/status` (proxy autenticado existente); tarjeta
  "Canales" del dashboard.

## Criterios de aceptación

- Con reservas mixtas sembradas, el bloque refleja conteos exactos por canal (FR-007).
- Con la BD caída, `/status` responde con `channels: []` (sin 500).
- Tiempo de respuesta total del endpoint < 5 s (SC-004; los checks ya tienen timeout).
