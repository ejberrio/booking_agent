# Quickstart: verificar calendario con ofertas y registro de deals

**Feature**: 015-calendar-offers

## Tests (sin APIs reales)

```bash
cd apps/api && uv run pytest -q       # CRUD, validaciones, solapes (abiertos/medio-abiertos), warning en preview
cd apps/web && npm run build
```

Escenarios clave:
1. CRUD: crear (con y sin fechas), editar, desactivar, borrar; validaciones 422 (canal, nombre, pct, fechas invertidas).
2. Solape: cerrado×cerrado, abierto total ("siempre activo"), medio-abierto, sin solape por fechas, sin solape por canal (`channels_scope=['airbnb']` vs deal booking), deal inactivo.
3. Preview de promoción: con deal solapante → warning que lo nombra; sin deals → warnings idénticos a los actuales (FR-010).
4. Migración: upgrade/downgrade limpios (enum channelkind con create_type=False).

## Verificación EN VIVO (el CRUD es local — bajo riesgo; la semilla requiere confirmación del host)

```bash
WEB="https://web-production-dfcaf.up.railway.app"

# 1) Semilla (CON CONFIRMACIÓN DEL HOST de los valores):
#    - "Vacaciones Julio · mín 3" (booking, 20%, 2026-07-03 → 2026-07-31)
#    - "Descuento semanal" (airbnb, 5%, siempre activo)
#    - "Descuento mensual" (airbnb, 25%, siempre activo)
curl -s -X POST -H "Cookie: session=ok" -H "Content-Type: application/json" \
  -d '{"channel":"booking","name":"Vacaciones Julio · mín 3","discount_pct":20,"date_from":"2026-07-03","date_to":"2026-07-31"}' \
  "$WEB/api/proxy/pricing/native-deals"

# 2) Calendario (navegador): julio 3-31 con punto cian + todos los días con datos
#    marcados por los deals de Airbnb; leyenda "Deal nativo"; clic en un día →
#    panel "Ofertas del día" con el detalle (canal, %, vigencia).
# 3) Advertencia real: preview de una promo de prueba jul 10-15 scope booking →
#    warning nombra "Vacaciones Julio"; scope ['airbnb'] con fechas de julio →
#    advierte semanal/mensual pero NO el de Booking. (Solo preview: NO aplicar.)
# 4) Desactivar un deal → su marcador desaparece del calendario al refrescar.
```

Nota: el registro no escribe al canal — no hay nada que revertir en Beds24/Booking/Airbnb.
