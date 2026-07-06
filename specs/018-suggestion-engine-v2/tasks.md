# Tasks: Motor de sugerencias v2 — explicable, con contexto y mercado

**Input**: Design documents from `/specs/018-suggestion-engine-v2/`
**Prerequisites**: plan.md, spec.md (clarify completado), research.md, data-model.md, contracts/engine-v2-api.md, quickstart.md

**Tests**: incluidos y extensos (Constitución IV: el cálculo de precios — subidas Y bajadas — es la lógica que más dinero puede costar).

**Organization**: Foundational = modelo/migración/puerto (lo usan todas). US5 (supersede) va temprano: US1/US2 la necesitan al persistir.

## Format: `[ID] [P?] [Story] Description`

- **[Story]**: US1 (explicables), US2 (bajistas), US3 (contexto/POIs), US4 (mercado), US5 (supersede)

## Path Conventions

Monorepo `apps/api/` y `apps/web/`, según plan.md.

---

## Phase 1: Foundational (bloqueante)

- [X] T001 Modelos: `apps/api/app/models/property.py` (+address String(300), latitude/longitude Numeric(9,6), nullable); `apps/api/app/models/market.py` (+`PointOfInterest`: name String(200), note String(300) nullable, date_from/date_to Date nullable, is_active bool); `apps/api/app/models/intelligence.py` (+`ScanConfig` fila única: zone String(200) nullable, queries_per_scan Integer default 12, event_kinds String(200) nullable; `MarketReference` +occupancy_pct Numeric(5,2) nullable +sample_size Integer nullable); `apps/api/app/models/enums.py` (SuggestionStatus + `superseded`); exportar nuevos en `models/__init__.py`
- [X] T002 Migración `apps/api/migrations/versions/f3a4b5c6d7e8_engine_v2.py` (down `e2f3a4b5c6d7`): columnas property, tablas point_of_interest y scan_config, columnas market_reference, y `ALTER TYPE suggestionstatus ADD VALUE 'superseded'` dentro de `op.get_context().autocommit_block()`; downgrade limpio (las columnas/tablas; el valor de enum NO se remueve — documentar en el docstring)
- [X] T003 Puerto de mercado: crear `apps/api/app/market/provider.py` (`MarketSnapshot` dataclass: zone, month, adr Decimal|None, occupancy_pct Decimal|None, sample_size int, source str; Protocol `MarketDataProvider.get_snapshot(zone, month) -> MarketSnapshot | None`)

**Checkpoint**: 221 tests previos verdes con los modelos nuevos.

---

## Phase 2: User Story 5 — Supersede (P1, requisito de persistencia de todas)

- [X] T004 [US5] En `apps/api/app/services/suggestion_engine.py`: helper `_supersede_overlapping(session, unit_type_id, date_from, date_to)` (proposed solapadas → superseded) y housekeeping `_supersede_expired(session, unit_type_id, today)` (proposed con date_to < hoy → superseded); se invocan al persistir cada sugerencia nueva y al inicio de la generación respectivamente
- [X] T005 [US5] Verificar/ajustar el flujo 014: `apply_suggestion`/`reject` sobre una superseded → 409 con estado real (ya cubierto por la validación de estados — añadir test); la lista de pendientes no las muestra (proposed/approved — ya es así, test)
- [X] T006 [US5] Tests en `apps/api/tests/test_suggestion_v2_engine.py` (parte supersede): nueva solapada supersede la anterior; equivalente exacta no crea nada; vencidas → superseded en housekeeping; applied/rejected/approved intactas

---

## Phase 3: User Story 3 — Contexto: ubicación y POIs (P1, alimenta el query builder)

- [X] T007 [US3] `apps/api/app/channels/base.py`: `RemoteProperty` +address/latitude/longitude (None default); `apps/api/app/channels/beds24_v2.py`: mapear del GET /properties; `apps/api/app/services/sync_service.py` `_upsert_property`: guardar/corregir ubicación
- [X] T008 [US3] Crear `apps/api/app/api/routes/pois.py`: CRUD `/pois` (patrón deals: validación nombre no vacío/fechas coherentes, 422/404) + `GET/PUT /scan-config` (fila única autocreada con defaults; effective_zone derivada = zone ?? city+address; 422 queries_per_scan ∉ [1,30]); registrar ambos prefijos en `apps/api/app/api/router.py`
- [X] T009 [US3] Query builder en `apps/api/app/services/intelligence_service.py`: construir consultas desde effective_zone + POIs activos (vigentes por fecha; incluyen sus fechas clave en la consulta) + event_kinds, respetando queries_per_scan; `IntelligenceRun.detail` reporta consultas usadas/presupuesto corto; `scripts/scan_daily.py` deja de usar QUERIES fijas
- [X] T010 [US3] Tests en `apps/api/tests/test_pois_api.py`: CRUD POIs + scan-config (validaciones, effective_zone); query builder (POI vencido no aparece, budget respetado); import persiste ubicación (extender suite de sync)

---

## Phase 4: User Story 4 — Mercado (P2, ancla del cálculo)

- [X] T011 [US4] Crear `apps/api/app/market/tavily_market.py`: `TavilyMarketProvider(search, llm)` — consultas dirigidas de tarifas de la zona/mes, extracción LLM de precios por noche (patrón extract_events), MEDIANA + sample_size → `MarketSnapshot`; 0 muestras → None; persiste/actualiza `MarketReference` (source="tavily", occupancy_pct=None honesto)
- [X] T012 [US4] Tests (en `apps/api/tests/test_suggestion_v2_engine.py` o archivo propio): extracción→mediana con dobles; 0 muestras → None; <3 muestras → snapshot marcado de baja confianza; persistencia en MarketReference

---

## Phase 5: User Story 1 + 2 — Motor: explicable y simétrico (P1, el corazón)

- [X] T013 [US1] Reescribir `apps/api/app/domain/suggestion.py` (v2): entrada (base, señales: evento con metadatos, ocupación, gap_days_ahead, snapshot de mercado; regla min/max) → salida `SuggestionOutputV2(price, factors[], confidence)`; señales alcistas actuales conservadas + BAJISTAS: hueco ≤14 días (descuento progresivo: más cerca ⇒ mayor, tope −15%), valle con mercado por debajo (ancla ponderada); límites SIEMPRE: piso min_price, techo max_price, tope bajista −15%; factors con kind/label/pct y evento con name/location/dates/source_url
- [X] T014 [US1] Reescribir `apps/api/app/services/suggestion_engine.py` (v2): recorrer horizonte agrupando por (evento → su rango) y (señal no-evento → días contiguos misma señal y mismo precio base, cortar al cambiar base); EXCLUIR noches con reserva confirmada; construir `rationale = {text resumen, factors, market}` (retrocompatible); persistir con supersede (T004); una sugerencia por rango
- [X] T015 [US2] Cablear el scan: `intelligence_service.scan` pasa el MarketDataProvider (Tavily) y el calendario/reservas al motor; mantener la firma pública compatible con el cron
- [X] T016 [US1] Tests de dominio en `apps/api/tests/test_suggestion_v2_domain.py`: subida por evento con desglose; ocupación; hueco a 3/9/14 días (progresivo, tope −15%); piso min_price y techo max_price; mercado-ancla; sin mercado → sin factor market; confidence por nº de señales
- [X] T017 [US1] Tests de motor en `apps/api/tests/test_suggestion_v2_engine.py`: evento multi-día → 1 sugerencia de rango con evento en factors; días contiguos misma señal → 1 rango; corte al cambiar precio base; reservas excluidas; rationale.text presente (compatibilidad v1); scan end-to-end con dobles (search+LLM+market falsos); ACTUALIZAR las suites v1 al contrato v2 (test_suggestion_engine.py, tests de generate en test_intelligence_service.py, test_suggestions.py si aplica)

---

## Phase 6: Web (US1/US3)

- [ ] T018 [P] [US1] `apps/web/lib/types.ts`: `Suggestion.rationale` gana `factors?`/`market?` tipados; `Poi`, `ScanConfig`; `apps/web/lib/api.ts`: CRUD pois + get/update scan-config
- [ ] T019 [US1] `apps/web/components/suggestions/suggestion-card.tsx` y `apps/web/components/calendar/suggestion-panel.tsx`: si `rationale.factors` existe → chips por factor (± % con signo; evento con nombre/lugar y enlace a source_url; mercado con muestras); fallback a `rationale.text` (v1)
- [ ] T020 [US3] `apps/web/app/(app)/settings/page.tsx`: tarjeta "Sitios de interés (POIs)" (CRUD, patrón deals de la 015) y tarjeta "Escaneo" (zona efectiva, consultas por corrida, tipos de evento)

---

## Phase 7: Polish & Cross-Cutting

- [ ] T021 [P] `docs/adr/0006-suggestion-engine-v2.md` (señales/límites decididos por el host, agrupación, supersede, puerto de mercado + research AirDNA/PriceLabs con el porqué del candidato) y sección en `docs/operations.md` (POIs, scan config, cómo leer el racional)
- [ ] T022 Verificación final: `uv run pytest -q` + ruff; `npm run build`; `alembic heads` único; FR-008 (flujo 014 intacto)
- [ ] T023 Verificación EN VIVO tras merge: re-import (ubicación real persistida); semilla POIs Daviarena (2026-09-01→2026-11-30, "muy cerca del apartamento") + CC Mayorca ("al frente"); disparar scan y revisar: pendientes viejas superseded, sugerencias nuevas POR RANGO con factores/evento/fuente, mercado con muestras o ausencia honesta; UI (lista, panel, chat); NO aplicar sugerencias sin decisión del host

---

## Dependencies & Execution Order

```
T001-T003 ─▶ T004-T006 (supersede) ─▶ T013-T017 (motor) ─▶ T018-T020 (web) ─▶ T021-T022 ─▶ merge ─▶ T023
           └▶ T007-T010 (contexto) ─┬▶ T015 (cableado del scan)
           └▶ T011-T012 (mercado) ──┘
```

- US3 y US4 pueden ir en paralelo tras Foundational; el motor (Phase 5) los consume.
- T018 ∥ T019 tras el backend; T020 tras T008.

## Implementation Strategy

Incrementos: Foundational+supersede (depura el problema actual) → contexto+mercado (insumos) → motor (corazón) → web. Una rama/PR; commits por fase; T023 con el cron o un disparo manual del scan.
