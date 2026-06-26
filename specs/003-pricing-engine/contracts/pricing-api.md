# Contrato — API y casos de uso del motor de precios

Capa de aplicación (`pricing_app_service`, `promotion_service`) y endpoints. La publicación usa el puerto `ChannelManager` (inyectado; falso en tests).

## Casos de uso (servicio)

```python
async def get_calendar(session, unit_type_id, date_from, date_to) -> list[CalendarDayView]: ...

async def set_day_price(session, channel, *, unit_type_id, day, price, origin) -> ApplyResult: ...
    # valida regla -> set_base_price (auditado) -> publica efectivo. Rechaza si fuera de límites.

async def preview_range(session, *, unit_type_id, selection: RangeSelection, price) -> ChangePreview: ...
    # NO aplica. Marca días inválidos. Calcula fingerprint.

async def apply_range(session, channel, *, unit_type_id, selection, price, fingerprint, origin) -> ApplyResult: ...
    # si fingerprint obsoleto -> ApplyResult(stale=True) sin aplicar.
    # aplica solo días válidos: set_base_price (auditado) + publica efectivo (agrupado).

async def rollback_and_publish(session, channel, change_id, *, confirm=False) -> ApplyResult: ...
    # audit_service.rollback_change (conflicto si hay cambios posteriores) -> publica efectivo.

async def history(session, unit_type_id, date_from, date_to) -> list[PriceChangeLog]: ...
```

```python
# promotion_service
async def create_promotion(session, channel, **fields) -> Promotion: ...   # audita + recalcula + re-publica
async def update_promotion(session, channel, promotion_id, **fields) -> Promotion: ...
async def delete_promotion(session, channel, promotion_id) -> None: ...
```

## Endpoints (`/pricing`)

| Método | Ruta | Cuerpo / Query | Acción |
|--------|------|----------------|--------|
| GET | `/pricing/calendar` | unit_type_id, from, to | lista `CalendarDayView` |
| POST | `/pricing/day` | unit_type_id, day, price | fija precio de un día (valida, audita, publica) |
| POST | `/pricing/range/preview` | unit_type_id, selection, price | devuelve `ChangePreview` (diff + fingerprint) |
| POST | `/pricing/range/apply` | unit_type_id, selection, price, fingerprint | aplica válidos; `stale` si obsoleto |
| POST | `/pricing/rollback` | change_id, confirm | revierte (conflicto → requiere confirm) y publica |
| GET | `/pricing/history` | unit_type_id, from, to | historial de cambios |
| POST/PUT/DELETE | `/pricing/promotions[/{id}]` | datos de promoción | CRUD + auditoría + re-publicación del efectivo |

## Garantías de comportamiento

- **G1**: `set_day_price`/`apply_range` rechazan/excluyen precios fuera de los límites de la propiedad; nunca se auditan ni publican esos días.
- **G2**: `apply_range` aplica solo días válidos; los inválidos se devuelven en `skipped_invalid`.
- **G3**: Si el estado base cambió entre preview y apply (fingerprint distinto), `apply_range` devuelve `stale=True` y NO aplica.
- **G4**: Toda aplicación de precio audita (PriceChangeLog) y publica el **efectivo** vía el puerto; si la publicación no se verifica, se registra incidencia y el cambio local se conserva.
- **G5**: Promos solapadas → efectivo = mayor descuento (no acumula).
- **G6**: CRUD de promoción → `PromotionChangeLog` + recálculo + re-publicación del efectivo de los días afectados.
- **G7**: Rollback con cambios posteriores → requiere `confirm`; tras revertir, se publica el efectivo.

## Contrato de pruebas

| Test | Verifica |
|------|----------|
| `test_pricing_app::test_get_calendar_base_and_effective` | base, efectivo, disponibilidad y promos por día |
| `test_pricing_app::test_set_day_validates_and_publishes` | fuera de límites rechazado (G1); válido audita + publica efectivo (G4) |
| `test_pricing_app::test_preview_marks_invalid_and_weekday_filter` | filtro por día de semana; inválidos marcados (G2) |
| `test_pricing_app::test_apply_skips_invalid_applies_valid` | aplica válidos, excluye inválidos (G2) |
| `test_pricing_app::test_apply_stale_preview_blocks` | fingerprint obsoleto → `stale=True`, sin aplicar (G3) |
| `test_pricing_app::test_rollback_then_publishes` | revierte y publica; conflicto exige confirm (G7) |
| `test_promotion_service::test_create_promo_audits_and_republishes` | promo creada → PromotionChangeLog + re-publica efectivo (G6) |
| `test_promotion_service::test_overlap_takes_max` | efectivo = mayor descuento (G5) |
