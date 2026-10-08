# Quickstart: Sugerencias accionables (019)

## Local

```bash
cd apps/api && uv run pytest -q tests/test_suggestion_blocks.py tests/test_suggestion_batch.py tests/test_suggestion_engine.py
cd apps/web && npm run build
```

## Escenarios de validación (producción, tras el deploy)

1. **Vendibles (US1)**: `GET /suggestions/blocks` no incluye noches del 9–12 oct (reservadas) ni noches bloqueadas; `hidden_occupied` las cuenta.
2. **Reaparición (US1)**: con una reserva de prueba cancelada y sincronizada, sus noches vuelven a `blocks` sin correr el scan (verificable en tests; en prod solo si ocurre una cancelación real).
3. **Bloques (US3)**: las sugerencias de "Martin Garrix" (1 y 5 dic) aparecen en un único bloque `event`; los días "libre a N días" contiguos forman un bloque `period`.
4. **Vista previa (US2)**: seleccionar 2 bloques → `batch/preview` devuelve todas sus noches con antes/después y huella.
5. **Stale (US2)**: cambiar el precio de una noche del lote entre preview y apply → `batch/apply` responde 409 y no escribe.
6. **Aplicación (US2)**: confirmar el lote → noches publicadas (calendario las muestra), sugerencias `applied`, auditoría con `origin=suggestion`. ⚠️ En producción solo con confirmación del host (Principio III); en la verificación se usan tests con canal falso.
7. **Racional (US4)**: tras el scan, ninguna pendiente muestra "mercado ~83000" (dato descartado).
8. **Calendario sin cambios**: los marcadores violeta siguen en las mismas noches que antes.
