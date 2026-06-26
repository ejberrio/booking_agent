# Quickstart — Motor de precios

Cómo usar y verificar el motor de precios una vez implementado (`/speckit-implement`).

## 1. Migración (nueva tabla de auditoría de promos)

```bash
cd apps/api
uv run alembic revision --autogenerate -m "auditoria de promociones"
uv run alembic upgrade head
```

## 2. Verificación funcional (con la API corriendo)

```bash
make api   # :8000
```
Requiere una propiedad/unidad ya importada (feature 002, `POST /sync/import`).

1. **Consultar**: `GET /pricing/calendar?unit_type_id=1&from=2026-07-01&to=2026-07-31` → por día: base, efectivo, disponibilidad, promos.
2. **Día**: `POST /pricing/day { unit_type_id, day, price }` → fija, audita y publica el efectivo a Beds24. Un precio fuera de límites se rechaza.
3. **Rango (preview)**: `POST /pricing/range/preview { unit_type_id, selection:{date_from,date_to,weekdays:[4,5]}, price }` → diff con días afectados (solo viernes/sábados), inválidos marcados, y un `fingerprint`.
4. **Rango (apply)**: `POST /pricing/range/apply { ..., fingerprint }` → aplica los válidos; si el estado cambió, responde `stale=true` (vuelve a previsualizar).
5. **Promoción**: `POST /pricing/promotions { ... 15% ... }` → baja el efectivo de los días cubiertos y **re-publica**; queda en la auditoría de promos.
6. **Rollback**: `POST /pricing/rollback { change_id }` → revierte (si hay cambios posteriores pide `confirm`) y re-publica el efectivo.
7. **Historial**: `GET /pricing/history?unit_type_id=1&from=...&to=...`.

## 3. Tests (sin API real)

```bash
cd apps/api
uv run pytest -q     # incluye test_pricing_app y test_promotion_service (ChannelManager falso)
uv run ruff check .
```
Criterio: contratos de `contracts/pricing-api.md` en verde; ninguna llamada real a Beds24 en los tests.
