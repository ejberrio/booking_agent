# Data Model: Sugerencias accionables (019)

**Sin migraciones.** Todas las entidades nuevas son derivadas (se calculan al consultar).

## PriceSuggestion (existente, `price_suggestion`)

Sin cambios de columnas. Cambios de comportamiento:
- `rationale` / `confidence`: se refrescan en el scan cuando la sugerencia `proposed/approved` es equivalente (US4).
- `status`: el lote puede pasar `proposed|approved → applied` (solo si ≥1 noche aplicada y 0 fallidas).
- `applied_change_id`: id del primer `price_change_log` creado por el lote para esa sugerencia.

## SellableNight (derivada)

| Campo | Tipo | Nota |
|---|---|---|
| date | date | ≥ hoy |
| suggestion_id | int | sugerencia pendiente de origen |
| current_price | Decimal \| None | precio base vigente |
| suggested_price | Decimal | precio de la sugerencia |

Regla: excluida si hay reserva `confirmed` con `check_in ≤ date < check_out`, si `calendar_day.is_blocked`, o si `units_available == 0`.

## SuggestionView (derivada, por sugerencia)

`id, date_from, date_to, suggested_price, rationale, confidence, status, sellable_nights: [date], occupied_count: int, total_nights: int`. No aparece si `sellable_nights` está vacío.

## SuggestionBlock (derivada, presentación)

| Campo | Tipo | Nota |
|---|---|---|
| key | str | `event:<nombre>` o `period:<kind>:<fecha inicio>` |
| kind | "event" \| "period" | |
| title | str | "Juanes", "Libre próximo", "Ocupación alta", "Otras" |
| date_from / date_to | date | primera y última noche vendible del bloque |
| nights | list[SellableNight] | ordenadas por fecha |
| suggestion_ids | list[int] | |
| direction | "up" \| "down" \| "mixed" | según precio sugerido vs actual |

## BatchPreview / BatchResult (derivadas)

- **BatchPreviewItem**: `date, suggestion_id, old_price, new_price, valid, reason` — `reason ∈ {reservada, bloqueada, pasada, fuera de límites, sugerencia resuelta, conflicto}`.
- **BatchPreview**: `items, fingerprint, valid_count, skipped_count, suggestion_ids`.
- **BatchResultNight**: `date, suggestion_id, status ∈ {applied, skipped, failed}, reason`.
- **BatchResult**: `nights, applied_count, skipped_count, failed_count, suggestions: {id: applied|pending|unchanged}`, `stale: bool`.

## Transiciones

```
proposed|approved ──lote: ≥1 aplicada ∧ 0 fallidas──▶ applied
proposed|approved ──lote: alguna fallida──▶ (sin cambio, sigue pendiente)
proposed|approved ──lote: todas omitidas──▶ (sin cambio)
```
