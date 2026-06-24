# Quickstart — Modelo de datos

Cómo aplicar y verificar el modelo una vez implementado (`/speckit-implement`).

## 1. Levantar Postgres y aplicar migraciones

```bash
make db-up                          # Postgres en docker
cd apps/api
uv run alembic revision --autogenerate -m "modelo de datos inicial"
uv run alembic upgrade head
```

## 2. Verificación funcional (flujo mínimo)

El siguiente recorrido valida las historias P1/P2 de la spec:

1. Crear una **Property** (Medellín, COP) con un **Channel** Booking activo y un **UnitType** (`units_count=1`).
2. Fijar el **Rate.base_price** de una fecha → verificar que se crea un **PriceChangeLog** (`origin=manual`).
3. Consultar el **precio efectivo** de esa fecha sin promociones → igual al base.
4. Crear una **Promotion** del 10% que cubra esa fecha → el efectivo refleja el descuento.
5. Crear una segunda **Promotion** del 20% solapada → el efectivo usa **solo** la del 20% (no 30%).
6. Definir **PricingRule** con `min_price` → intentar un precio por debajo → se señala inválido.
7. Cambiar el precio de nuevo y luego **revertir** el último cambio → vuelve al valor anterior; se registra un PriceChangeLog `origin=rollback`.
8. Registrar una **Booking** confirmada para esa noche → `units_available` baja a 0 (compartido entre canales).
9. Insertar un **Event** dos veces con los mismos datos → no se duplica.
10. Crear una **PriceSuggestion** (proposed) → aprobar → aplicar → su estado pasa a `applied` y enlaza el PriceChangeLog.

## 3. Tests

```bash
cd apps/api
uv run pytest -q            # incluye test_models, test_pricing, test_audit
uv run ruff check .
```

Criterio de aceptación: todos los tests del contrato (`contracts/data-access.md`) en verde.
