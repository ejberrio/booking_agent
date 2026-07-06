# Implementation Plan: Motor de sugerencias v2

**Branch**: `018-suggestion-engine-v2` | **Date**: 2026-07-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-suggestion-engine-v2/spec.md` (clarify completado)

## Summary

Reescritura del `suggestion_engine` alrededor de tres piezas: (1) **contexto** — la propiedad gana ubicación real (address/lat/lon del schema de Beds24, ya disponible en GET /properties) + registro manual de POIs que dirigen las búsquedas; (2) **señales simétricas y agrupadas** — las alcistas actuales + bajistas nuevas (huecos ≤14 días, valle, mercado por debajo; piso min_price, tope −15%), agrupadas POR RANGO (evento o días contiguos con la misma señal y mismo precio base) con racional ESTRUCTURADO (JSON en `rationale`, retrocompatible con `text`); (3) **puerto `MarketDataProvider`** — implementación gratis (búsquedas Tavily dirigidas + extracción LLM de tarifas → mediana con sample_size a `MarketReference`) y adaptador pago enchufable por config (research: PriceLabs es el candidato realista — API de cliente y ~USD 10/mes en Colombia; AirDNA API es solo enterprise). Supersede: un scan nuevo reemplaza pendientes solapadas (estado nuevo `superseded`) y depura vencidas — limpia las ~130 acumuladas en el primer scan.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: existentes (Tavily vía httpx, LiteLLM para extracción, SQLAlchemy async); SIN dependencias nuevas
**Storage**: PostgreSQL / SQLite tests. **UNA migración** (`f3a4b5c6d7e8`, down `e2f3a4b5c6d7`): columnas de ubicación en property, tabla `point_of_interest`, tabla `scan_config` (fila única), columnas `occupancy_pct`/`sample_size` en market_reference, y valor `superseded` en el enum suggestionstatus (autocommit_block en PG)
**Testing**: pytest con dobles (search/LLM/market falsos); web `npm run build`
**Target Platform**: Railway; el scan diario (cron) es el consumidor principal del motor
**Project Type**: monorepo web application
**Performance Goals**: scan diario ≤ ~15 consultas Tavily (config editable; free tier 1000/mes)
**Constraints**: honestidad (sin datos de mercado → se dice, no se inventa); piso min_price / tope −15%; reservas confirmadas jamás reciben sugerencia; no romper 221 tests; el flujo 014 (aprobar-y-aplicar) funciona sin cambios con rangos
**Scale/Scope**: single-tenant; la feature MÁS grande de la tanda (~10 archivos API + ~4 web + 1 migración)

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo con clarify (4 decisiones del host); **ADR 0006** (motor v2 y puerto de mercado) |
| II. Provider-agnostic | ✅ `MarketDataProvider` es puerto neutro (get_snapshot(zone, month) → adr/occupancy/samples/source); Tavily y el pago son adaptadores; nada propietario en el motor |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ el motor solo PROPONE (status proposed); aplicar sigue siendo la acción única de 014 con el host; supersede solo toca pendientes (proposed), jamás resueltas |
| IV. Tipado y pruebas | ✅ el cálculo de precios (subidas Y bajadas con piso/tope) es la lógica que más dinero puede costar → suite dedicada del dominio + agrupación + supersede |
| V. Simplicidad | ✅ sin colas ni jobs nuevos (mismo cron); el proveedor pago se DOCUMENTA y el puerto queda listo, pero no se construye un adaptador sin cuenta que lo pruebe (YAGNI honesto) |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

```text
apps/api/
├── app/models/property.py               # + address/latitude/longitude (nullable)
├── app/models/market.py                 # PriceSuggestion sin cambios de columnas; POI NUEVO aquí
├── app/models/intelligence.py           # MarketReference + occupancy_pct/sample_size; ScanConfig NUEVO
├── app/models/enums.py                  # SuggestionStatus + superseded
├── migrations/versions/f3a4b5c6d7e8_engine_v2.py
├── app/channels/base.py                 # RemoteProperty + address/lat/lon
├── app/channels/beds24_v2.py            # mapea ubicación de GET /properties
├── app/services/sync_service.py         # upsert de ubicación en property
├── app/market/provider.py               # NUEVO: puerto MarketDataProvider + snapshot
├── app/market/tavily_market.py          # NUEVO: proveedor gratis (búsqueda dirigida + extracción LLM → mediana)
├── app/domain/suggestion.py             # v2: señales simétricas, piso/tope, desglose de factores
├── app/services/suggestion_engine.py    # v2: agrupación por rango, supersede, racional estructurado
├── app/services/intelligence_service.py # scan: query builder con POIs/zona/config
├── app/api/routes/pois.py               # NUEVO: CRUD /pois + GET/PUT /scan-config
└── tests/test_suggestion_v2_domain.py + test_suggestion_v2_engine.py + test_pois_api.py

apps/web/
├── app/(app)/settings/page.tsx          # tarjetas POIs + Configuración del scan
├── components/suggestions/suggestion-card.tsx  # racional estructurado (factores + evento con fuente)
├── components/calendar/suggestion-panel.tsx    # ídem
└── lib/{types,api}.ts

docs/adr/0006-suggestion-engine-v2.md · docs/operations.md
```

## Decisiones clave (detalle en research.md)

1. **Ubicación desde el CM**: el schema oficial de Beds24 expone address/city/latitude/longitude en GET /properties → `RemoteProperty` gana los campos, el import los persiste (columnas nullable). La "zona" de búsqueda default = `city` + address; editable en scan_config.
2. **Racional estructurado retrocompatible**: `rationale` (JSONB existente) gana `factors: [{kind, label, pct, event?{name,location,dates,source_url}}]` y `market?{adr,samples,source}` manteniendo `text` (resumen) → las sugerencias v1 pendientes/históricas siguen renderizando; la UI muestra factores si existen.
3. **Agrupación por rango**: una sugerencia por (señal dominante × rango contiguo × mismo precio base). El modelo ya tiene date_from/date_to y el apply de 014 ya itera rangos → cero cambios en el flujo de resolución.
4. **Supersede**: estado nuevo `superseded` (terminal, auditable); al crear una sugerencia de rango R se supersede toda proposed solapada con R; housekeeping: proposed totalmente vencidas → superseded. Primer scan v2 depura las ~130. La lista de pendientes (014) no las muestra (proposed/approved solamente — ya es así).
5. **Puerto de mercado**: `MarketSnapshot(zone, month, adr, occupancy_pct|None, sample_size, source, fetched_at)`. Gratis: consultas Tavily dirigidas ("precio por noche apartamento {zona} {mes}") + extracción LLM de tarifas → mediana; se persiste en MarketReference (source="tavily"). **Pago (research)**: AirDNA API = solo Enterprise (custom, fuera de rango) → el candidato realista es **PriceLabs** (~USD 9.99/listing/mes en Colombia; Market Dashboard +9.99; API de cliente) — puerto listo, adaptador pago NO construido (sin cuenta que lo valide; documentado en ADR).
6. **Presupuesto**: `scan_config.queries_per_scan` (default 12); el scan reporta consultas usadas y si se quedó corto (detail del IntelligenceRun).

## Fase 0 → research.md · Fase 1 → data-model.md, contracts/, quickstart.md
