# Quickstart: verificar motor de sugerencias v2

**Feature**: 018-suggestion-engine-v2

## Tests (sin APIs reales)

```bash
cd apps/api && uv run pytest -q
cd apps/web && npm run build
```

Escenarios clave:
1. Dominio: subida por evento con desglose; bajada por hueco ≤14d (tope −15%, piso min_price); mercado como ancla; sin mercado → sin factor market.
2. Agrupación: evento multi-día → 1 sugerencia; días contiguos misma señal → 1 rango; corte al cambiar el precio base; reservas excluidas.
3. Supersede: nueva solapada → anterior superseded; equivalente → nada; vencidas → superseded; resueltas intactas; apply/reject de superseded → 409.
4. Proveedor gratis: extracción de tarifas (doble LLM) → mediana + sample_size; 0 muestras → None.
5. POIs/config: CRUD validado; query builder usa zona+POIs activos (con fechas) y respeta queries_per_scan.
6. Import: ubicación de la propiedad persistida/corregida.
7. Retrocompatibilidad: sugerencias v1 (solo text) siguen renderizando; 221 tests previos verdes.

## Verificación EN VIVO (tras merge)

```bash
WEB="https://web-production-dfcaf.up.railway.app"
# 1) Re-import → property con address/lat/lon reales.
# 2) Semilla POIs (host confirmó): Daviarena (sep-nov 2026) + CC Mayorca.
# 3) Disparar un scan (manual con railway run o esperar el cron) y revisar:
#    - IntelligenceRun.detail: consultas usadas, presupuesto.
#    - Las ~130 pendientes viejas quedaron superseded; las nuevas son POR RANGO.
#    - Racional: evento con nombre/lugar/fuente; factores con %; mercado con muestras.
# 4) UI: lista y panel del calendario muestran los factores; chat explica igual.
# 5) NO aplicar sugerencias reales sin decisión del host (el flujo 014 protege).
```
