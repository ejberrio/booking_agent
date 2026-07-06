# Data Model: Feature 018 — Motor de sugerencias v2

**UNA migración** `f3a4b5c6d7e8` (down `e2f3a4b5c6d7`).

## Property (existente — columnas nuevas, nullable)

| Campo | Tipo | Origen |
|---|---|---|
| address | String(300) nullable | GET /properties de Beds24 (import las guarda/corrige) |
| latitude / longitude | Numeric(9,6) nullable | ídem |

## PointOfInterest (NUEVA — app/models/market.py)

| Campo | Tipo | Regla |
|---|---|---|
| name | String(200) | requerido |
| note | String(300) nullable | distancia/contexto ("muy cerca del apartamento") |
| date_from / date_to | Date nullable | fechas clave (inauguración); NULL = siempre relevante |
| is_active | Boolean default true | inactivo/vencido no dirige búsquedas |

Semilla (host): Daviarena (2026-09-01→2026-11-30) y CC Mayorca (sin fechas).

## ScanConfig (NUEVA — fila única, app/models/intelligence.py)

| Campo | Tipo | Default |
|---|---|---|
| zone | String(200) nullable | NULL = city+address de la propiedad |
| queries_per_scan | Integer | 12 |
| event_kinds | String(200) nullable | NULL = todos |

## MarketReference (existente — columnas nuevas)

`occupancy_pct Numeric(5,2) nullable`, `sample_size Integer nullable`. El proveedor gratis escribe source="tavily", occupancy_pct=None (honesto).

## SuggestionStatus (enum — valor nuevo)

`proposed → approved → applied | rejected | superseded(NUEVO, terminal)`. PG: ADD VALUE en autocommit_block. Reglas: solo proposed puede pasar a superseded; el apply/reject de 014 rechaza superseded con el 409 existente ("estado real").

## PriceSuggestion.rationale (JSONB — estructura, sin cambio de columna)

```json
{
  "text": "resumen de una línea (compatible v1)",
  "factors": [
    {"kind": "event", "label": "Concierto inaugural", "pct": 30,
     "event": {"name": "...", "location": "Daviarena", "dates": "2026-09-12", "source_url": "..."}},
    {"kind": "occupancy", "label": "ocupación alta", "pct": 10},
    {"kind": "gap", "label": "libre a 9 días", "pct": -12},
    {"kind": "market", "label": "mercado ~$310.000 (5 tarifas)", "pct": null}
  ],
  "market": {"adr": "310000", "samples": 5, "source": "tavily", "fetched_at": "..."}
}
```

## MarketSnapshot (puerto, no persistido)

`(zone, month, adr: Decimal|None, occupancy_pct: Decimal|None, sample_size: int, source: str)` — el motor lo consume; el proveedor decide de dónde sale.
