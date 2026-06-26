# Data Model — Motor de precios

Reutiliza las entidades de la feature 001 (Rate, Promotion, PricingRule, PriceChangeLog, CalendarDay) y la publicación de la 002. Añade **una** tabla de auditoría de promociones; el resto son **objetos de valor transitorios** (no persistidos).

## Entidad nueva (persistida)

### PromotionChangeLog
Auditoría de cambios de promociones (crear/editar/eliminar). PostgreSQL / SQLAlchemy 2.0.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| promotion_id | int? | id de la promoción (null si eliminada) |
| action | enum(created, updated, deleted) | |
| before | JSONB? | snapshot previo (update/delete) |
| after | JSONB? | snapshot nuevo (create/update) |
| origin | enum(chat, manual, suggestion) | reutiliza ChangeOrigin (sin rollback) |
| changed_at | timestamptz | |

- Append-only (como `PriceChangeLog`).

## Objetos de valor (transitorios, en `app/schemas/pricing.py`)

### RangeSelection
Criterio de selección de días.
- `date_from: date`, `date_to: date`
- `weekdays: list[int] | None` (0=lunes … 6=domingo; None = todos)
- `days: list[date] | None` (lista explícita; si se da, tiene prioridad)
- Método de expansión → `list[date]`.

### CalendarDayView (respuesta de consulta)
- `date`, `base_price: Decimal | None`, `effective_price: Decimal | None`, `available: int`, `promotions: list[str]`.

### ChangePreviewDay
- `date`, `old_price: Decimal | None`, `new_price: Decimal`, `valid: bool`, `reason: str | None`.

### ChangePreview
- `items: list[ChangePreviewDay]`
- `fingerprint: str` (hash de los pares (date, old_price) afectados — para detectar obsolescencia)
- `has_invalid: bool`
- `valid_count: int`, `invalid_count: int`

### ApplyResult
- `applied_days: list[date]`, `skipped_invalid: list[date]`
- `audited: int`, `published: int`, `publish_issues: int`
- `stale: bool` (True si el preview estaba obsoleto y NO se aplicó)

## Reglas / invariantes (verificadas en servicio)
1. El precio efectivo se calcula con el dominio 001 (`effective_price`); promos solapadas → mayor descuento (no acumula).
2. `apply_range` aplica solo días `valid=True`; los inválidos van a `skipped_invalid`.
3. Si `fingerprint` esperado ≠ recalculado → `stale=True`, no se aplica nada.
4. Toda escritura de precio base pasa por `pricing_service.set_base_price` (auditada) y publica el efectivo vía el puerto.
5. Cambios de promoción → `PromotionChangeLog` + recálculo + re-publicación del efectivo de los días afectados.
6. Rollback vía `audit_service.rollback_change`; tras revertir, se publica el efectivo resultante.
