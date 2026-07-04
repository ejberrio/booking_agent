# Quickstart: verificar detalle de reservas y notas del host

**Feature**: 016-calendar-bookings-notes

## Tests (sin APIs reales)

```bash
cd apps/api && uv run pytest -q
cd apps/web && npm run build
```

Escenarios clave:
1. Adaptador V2: firstName+lastName → guest_name compuesto; parciales; vacío → None.
2. Import: nueva reserva con nombre; re-import corrige histórica sin nombre; remoto vacío NO borra nombre local; canal sin nombre no rompe.
3. GET /bookings: solape [check_in, check_out) con el rango; canceladas fuera; nights correcto.
4. CRUD notas: crear día único y rango, editar parcial, borrar; 422 (texto vacío, >500, fechas invertidas); solapes permitidos.
5. FR-010: sin datos nuevos, respuestas existentes idénticas.

## Verificación EN VIVO (todo lectura/local — sin nada que revertir en canales)

```bash
WEB="https://web-production-dfcaf.up.railway.app"

# 1) Re-import para capturar nombres de reservas existentes (lectura del CM, escritura local):
curl -s -X POST -H "Cookie: session=ok" -H "Content-Type: application/json" \
  -d '{"date_from":"2026-07-01","date_to":"2027-02-01"}' "$WEB/api/proxy/sync/import"
# 2) GET /bookings de agosto → la reserva real 6-19 ago con guest_name poblado.
# 3) Calendario (navegador): clic en un día de la reserva → panel con huésped/canal/noches;
#    clic en ago 19 (salida) NO la muestra.
# 4) Crear nota sobre el bloqueo oct 19-21 ("motivo del bloqueo…"), verla (punto lima),
#    editarla y conservarla (es dato real útil del host — confirmar el texto con él).
# 5) /status sin incidencias nuevas.
```
