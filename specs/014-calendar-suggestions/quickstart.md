# Quickstart: verificar sugerencias en el calendario y acción única

**Feature**: 014-calendar-suggestions

## Tests (sin APIs reales)

```bash
cd apps/api && uv run pytest -q       # resolve: estados, recorte, doble aplicación, fallo de canal
cd apps/web && npm run build
```

Escenarios clave con dobles:
1. `apply` sobre `proposed` → `applied`, precios publicados en todo el rango, `applied_change_id` enlazado, `applied_from == date_from`.
2. `apply` sobre `approved` histórica → funciona igual (FR-011).
3. `apply` sobre `applied`/`rejected` → 409 con estado real y CERO llamadas al canal (SC-004).
4. Rango parcialmente pasado → solo días `>= hoy` publicados; `applied_from == hoy`. Rango totalmente pasado → 409 "vencida", sin efectos.
5. Canal caído → SyncIssue registrada, sugerencia sigue `proposed`, error con mensaje claro.
6. `reject` sobre `approved` → `rejected` (simetría nueva); sobre `applied` → 409.
7. Ruta `approve` retirada → 404/405 (test de que no existe).

## Verificación EN VIVO (acotada y reversible — con confirmación del host)

```bash
WEB="https://web-production-dfcaf.up.railway.app"

# 1) Crear una sugerencia de prueba en fechas lejanas (o usar una vigente real).
# 2) Calendario: los días del rango muestran el punto violeta y la leyenda "Sugerencia".
# 3) Clic en un día marcado → panel con sugerido vs actual, rango, confianza, racional.
# 4) "Aprobar y aplicar" → toast de éxito; el marcador desaparece; el precio del día
#    se actualiza; en Beds24/canal se ve el precio nuevo (dar minutos a Airbnb).
# 5) Auditoría: GET /pricing/history muestra el cambio con origen "suggestion".
# 6) REVERTIR: rollback del cambio desde la historia (patrón existente) para no
#    dejar precios de prueba aplicados. ⚠️ Nunca dejar una sugerencia de prueba aplicada.
# 7) Lista de Sugerencias: solo dos botones; una sugerencia ya resuelta reintentada
#    desde otra pestaña → toast honesto con el estado real y refresco.
```
