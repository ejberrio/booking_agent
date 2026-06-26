# Data Model — Inteligencia de mercado y sugerencias

Reutiliza `Event` y `PriceSuggestion` (con justificación, confianza y estados proposed/approved/rejected/applied) y `event_service`/`suggestion_service` (001). Añade **dos** tablas; el resto son objetos de valor transitorios.

## Entidades nuevas (persistidas)

### MarketReference
Referencia de precio de mercado por zona (baseline simple en v1).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| zone | str | zona/ubicación (p. ej. "El Poblado") |
| reference_price | Numeric(12,2) | precio de referencia |
| source | str | cómo se obtuvo (p. ej. "baseline", "manual") |
| valid_from | Date? | opcional (vigencia) |
| valid_to | Date? | opcional |

### IntelligenceRun
Una corrida del escaneo (eventos + mercado + sugerencias).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| started_at | timestamptz | |
| finished_at | timestamptz? | |
| status | enum(running, success, partial, error) | reutiliza SyncStatus |
| events_found | int | |
| suggestions_created | int | |
| detail | str? | errores/resumen (sin secretos) |

## Objetos de valor (transitorios)

- **SearchResult** (`app/search/base.py`): título, contenido/resumen, url, score — salida del SearchProvider.
- **EventCandidate** (`app/market/extractor.py`): nombre, start_date, end_date?, kind, relevance, location — extraído por el LLM antes de normalizar/deduplicar en `Event`.
- **SuggestionInput / SuggestionOutput** (`app/domain/suggestion.py`): entrada (base, relevancia de evento, ocupación alta, ref de mercado, min/max) → salida (precio sugerido, justificación, confianza). Función PURA.

## Reglas / invariantes
1. Eventos: deduplicados por `dedup_key` (001); se descartan candidatos sin fecha utilizable.
2. Heurística: precio sugerido acotado a [min, max]; con justificación y confianza siempre presentes.
3. No se crea una sugerencia equivalente (unidad/día/precio) si ya existe `proposed`/`approved`/`applied`/`rejected` vigente para ese día.
4. Aplicar una sugerencia usa el motor de precios (003) con origen=sugerencia (audita + publica); la sugerencia pasa a `applied` y enlaza el cambio.
5. Ninguna sugerencia se aplica sin aprobación del host.
6. `MarketReference` ausente → las sugerencias se generan igualmente (sin fallo).
