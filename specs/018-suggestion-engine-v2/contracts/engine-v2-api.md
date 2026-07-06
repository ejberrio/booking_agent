# Contract: Motor v2 — POIs, configuración del scan y racional estructurado

**Feature**: 018-suggestion-engine-v2

## `GET/POST/PATCH/DELETE /pois`

Mismo patrón CRUD local de deals/notas (sin fingerprint, cero llamadas al CM):

```json
{ "pois": [ { "id": 1, "name": "Daviarena", "note": "muy cerca del apartamento",
  "date_from": "2026-09-01", "date_to": "2026-11-30", "is_active": true } ] }
```

422: nombre vacío, fechas invertidas. 404: id inexistente.

## `GET /scan-config` · `PUT /scan-config`

```json
{ "zone": null, "effective_zone": "Sabaneta, Cra 48…（city+address)", "queries_per_scan": 12, "event_kinds": null }
```

PUT parcial; 422 queries_per_scan fuera de [1, 30].

## `GET /suggestions` (extensión retrocompatible)

Cada sugerencia expone `rationale` completo (ya viaja); v2 añade DENTRO del JSON `factors[]` y `market{}` (ver data-model). `text` se mantiene SIEMPRE (v1 y superficies de chat). Sin cambios de shape fuera de rationale.

## Motor (contrato interno)

- Entrada: horizonte (hoy→+180), eventos (con POI/lugar/fuente), calendario (reservas/bloqueos/precios), regla de precios, MarketSnapshot opcional.
- Salida: sugerencias por RANGO (evento, o días contiguos misma señal y mismo precio base), cada una con factors y pct total acotado (piso min_price, techo max_price, tope bajista −15%).
- Noches con reserva confirmada: excluidas de cualquier rango.
- Supersede: al persistir rango R → proposed solapadas con R pasan a `superseded`; housekeeping: proposed vencidas → superseded. Equivalentes exactas → no se crea.
- Sin snapshot de mercado o con <3 muestras: el factor market no aparece o aparece marcado "confianza baja"; NUNCA se inventa.

## Puerto MarketDataProvider

```python
class MarketDataProvider(Protocol):
    async def get_snapshot(self, zone: str, month: date) -> MarketSnapshot | None: ...
```

Implementaciones: `TavilyMarketProvider` (gratis, esta feature) y futuro `PriceLabsProvider` (config `market_provider`, ADR 0006). `None` = sin datos (honesto).

## Web

- Configuración: tarjeta "Sitios de interés (POIs)" (CRUD, patrón deals) y tarjeta "Escaneo" (zona efectiva, consultas por corrida, tipos de evento).
- SuggestionCard y SuggestionPanel: si `rationale.factors` existe → chips por factor (evento con nombre/lugar y enlace a la fuente; % con signo); si no → `rationale.text` (v1, sin cambios).

## Criterios de aceptación

- Un evento del Daviarena genera UNA sugerencia por su rango, con nombre/lugar/fechas/fuente visibles y desglose del %.
- Noches libres a ≤14 días sin señales generan sugerencia de DESCUENTO (≥ −15%, ≥ min_price) con su porqué.
- Un segundo scan con señal distinta supersede la pendiente solapada (nunca dos pendientes para la misma noche); el primer scan v2 depura las ~130 acumuladas.
- Sin datos de mercado: sugerencias solo con señales propias y racional que lo dice.
- El apply de 014 sobre una sugerencia de rango publica todo el rango (comportamiento existente) y los 221 tests siguen verdes.
