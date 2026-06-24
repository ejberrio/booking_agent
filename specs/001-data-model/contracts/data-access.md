# Contrato interno de acceso a datos

Esta feature no expone endpoints HTTP (eso son features posteriores). El "contrato" que entrega al resto del sistema es el conjunto de **funciones de dominio puras** y los **invariantes de persistencia** sobre los que se apoyarán el motor de precios, el agente y la API.

## Funciones de dominio (puras, sin I/O) — `app/domain/pricing.py`

```python
def effective_price(base_price: Decimal, promotions: list[Promotion], rule: PricingRule | None, day: date) -> Decimal:
    """Precio efectivo de un día.
    - Aplica SOLO la promoción de mayor descuento vigente ese día (no acumula).
    - Acota al rango [min_price, max_price] de la regla si está definida.
    """

def best_promotion(promotions: list[Promotion], day: date) -> Promotion | None:
    """Promoción de mayor descuento efectivo vigente en `day`, o None."""

def violates_rule(price: Decimal, rule: PricingRule | None) -> bool:
    """True si `price` queda fuera de [min, max]."""
```

Estas funciones son el núcleo testeable (no requieren base de datos).

## Invariantes de persistencia (garantías para los consumidores)

- **C1 — Precio único por (unidad, día)**: a lo sumo una fila `Rate` por `(unit_type_id, date)`; consultar el precio base de un día es determinista.
- **C2 — Efectivo derivado**: el precio efectivo nunca se lee de la base; siempre se calcula con `effective_price(...)`. No hay dos fuentes de verdad.
- **C3 — Disponibilidad compartida**: la disponibilidad es por `(unit_type_id, date)`; cualquier reserva confirmada (de cualquier canal) la reduce. No existe disponibilidad por canal.
- **C4 — Auditoría completa**: toda escritura de `Rate.base_price` produce exactamente una fila `PriceChangeLog` con `old_price`, `new_price`, `origin` y `changed_at`. (Garantía a nivel de servicio de escritura, no de trigger en esta feature.)
- **C5 — Append-only**: `PriceChangeLog` no se actualiza ni borra.
- **C6 — Rollback auditado**: revertir = nueva fila `PriceChangeLog(origin=rollback, reverts_change_id=...)`. Si hay filas con `changed_at` posterior al cambio objetivo para la misma `(unit_type_id, date)`, la operación retorna un **conflicto** que exige confirmación; sin confirmación no escribe.
- **C7 — Sugerencia trazable**: una `PriceSuggestion` en estado `applied` referencia el `PriceChangeLog` que produjo (`applied_change_id`).
- **C8 — Evento idempotente**: insertar un evento con un `dedup_key` existente no crea duplicado (upsert).

## Contratos de prueba (qué deben verificar los tests)

| Test | Verifica |
|------|----------|
| `test_pricing::test_effective_no_promo` | efectivo == base cuando no hay promos |
| `test_pricing::test_overlapping_promos_takes_max` | gana la de mayor descuento, no se suman (C2, Q1) |
| `test_pricing::test_clamp_to_rule` | efectivo acotado a min/max |
| `test_audit::test_change_creates_log` | cada cambio crea un PriceChangeLog (C4) |
| `test_audit::test_rollback_restores` | rollback restaura valor anterior como nuevo registro (C6) |
| `test_audit::test_rollback_conflict_requires_confirm` | conflicto si hay cambios posteriores (C6, Q2) |
| `test_models::test_event_dedup` | dedup_key idempotente (C8) |
| `test_models::test_availability_shared` | reserva reduce disponibilidad para la unidad (C3) |
