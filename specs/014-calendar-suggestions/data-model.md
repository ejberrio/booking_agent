# Data Model: Feature 014 — Sugerencias en el calendario + acción única

**Sin migraciones**: ningún modelo cambia de estructura. Esta feature solo refina transiciones y añade vistas derivadas.

## PriceSuggestion (existente, sin cambios de esquema)

| Campo | Tipo | Nota |
|---|---|---|
| property_id / unit_type_id | FK | sin cambios |
| date_from / date_to | Date | rango de noches sugeridas |
| suggested_price | Numeric(12,2) | |
| rationale | JSONB | `{"text": ...}` — se muestra tal cual (mejorarlo es #98) |
| confidence | Numeric(4,3) | 0–1, se muestra como % |
| status | Enum SuggestionStatus | `proposed / approved / rejected / applied` |
| applied_change_id | int nullable | enlace al price_change_log (auditoría) |

### Transiciones de estado (lo que cambia)

**Antes** (dos pasos): `proposed → approved → applied` | `proposed → rejected`; `apply` sin validación de estado (bug latente: re-aplicable).

**Después** (acción única):

```
proposed  ──apply──▶ applied     (aprueba+aplica+publica en una operación)
proposed  ──reject─▶ rejected
approved  ──apply──▶ applied     (históricas aprobadas-sin-aplicar siguen resolubles)
approved  ──reject─▶ rejected    (simetría; cambio de una línea, ver R2)
applied / rejected ──▶ (terminal: cualquier intento → conflicto 409 con estado real)
```

Reglas de `apply` (FR-001/003/009/010):
- Solo `proposed` o `approved`; otro estado → conflicto honesto (sin efectos).
- `effective_from = max(date_from, hoy)`; si `date_to < hoy` → conflicto "vencida" (sin efectos).
- Publicación día a día vía `set_day_price(origin=suggestion)` (auditoría existente); `applied_change_id` = último cambio del primer día aplicado.
- Fallo del canal → `SyncIssue` + sin commit: la sugerencia permanece en su estado previo.

## SyncIssue (existente)

Gana un uso más: `kind=comm_error` (o el kind existente equivalente) cuando la publicación de una sugerencia falla. Sin cambios de esquema.

## Vistas derivadas (no persistidas)

- **Sugerencia vigente**: `status == proposed` **y** `date_to >= hoy`. (Las `approved` históricas NO se marcan en el calendario — ya fueron decididas; se resuelven desde la lista.)
- **Día del calendario (web)**: `suggestionsByDate: Map<fecha, Suggestion[]>` computado en el cliente cruzando la lista `proposed` con los días del mes visible; `suggestionDates: Set<fecha>` alimenta el marcador del componente calendario.
