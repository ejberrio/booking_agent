---
description: "Task list — Inteligencia de mercado y sugerencias"
---

# Tasks: Inteligencia de mercado y sugerencias de precio

**Input**: Design documents from `specs/005-market-intelligence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/intelligence-contract.md

**Tests**: INCLUIDOS (constitución IV). Con **SearchProvider / LLM / MarketReference / ChannelManager falsos** — sin APIs reales ni créditos.

**Organización**: por historia (US1–US6). Trabajo en `apps/api`. Reutiliza Event/PriceSuggestion + servicios de 001, motor de precios 003, conector 002, agente 004.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivo distinto, sin dependencias pendientes.
- **[Story]**: US1–US6.

---

## Phase 1: Setup

- [ ] T001 [P] Crear paquetes `app/search/` y `app/market/` (con `__init__.py`) en `apps/api/app/`

---

## Phase 2: Foundational (interfaces + modelos)

**⚠️ Bloqueante para todas las historias.**

- [ ] T002 [P] `SearchProvider` (Protocol) + `SearchResult` (DTO) en `apps/api/app/search/base.py`
- [ ] T003 [P] `MarketReference` (Protocol) en `apps/api/app/market/reference.py`
- [ ] T004 [P] Modelos `IntelligenceRun` y `MarketReference` (tabla) en `apps/api/app/models/intelligence.py` (reusa `SyncStatus`; registrar en `app/models/__init__.py`)
- [ ] T005 Migración Alembic para `intelligence_run` y `market_reference` en `apps/api/migrations/versions/`

**Checkpoint**: interfaces y tablas listas.

---

## Phase 3: User Story 1 - Descubrir e ingestar eventos (Priority: P1) 🎯 MVP

**Goal**: Buscar eventos de Medellín, parsearlos con el LLM y guardarlos sin duplicar.

**Independent Test**: Ejecutar un escaneo de eventos (con dobles) → eventos con fecha/tipo/relevancia; repetir → sin duplicados; candidato sin fecha descartado.

### Tests for User Story 1

- [ ] T006 [P] [US1] Test: extracción LLM → `EventCandidate`; upsert deduplicado (2ª corrida no duplica); candidato sin fecha descartado, en `apps/api/tests/test_intelligence_service.py`

### Implementation for User Story 1

- [ ] T007 [US1] `TavilyProvider` (httpx + caché simple) en `apps/api/app/search/tavily.py`
- [ ] T008 [US1] `event_extractor.extract_events(llm, results)` → `EventCandidate` (descarta sin fecha) en `apps/api/app/market/extractor.py`
- [ ] T009 [US1] `intelligence_service.scan_events` (buscar → extraer → upsert vía `event_service`) en `apps/api/app/services/intelligence_service.py`

**Checkpoint**: eventos descubiertos y deduplicados (MVP).

---

## Phase 4: User Story 2 - Generar sugerencias explicables (Priority: P1)

**Goal**: Heurística que combina evento + ocupación + mercado → sugerencias con justificación y confianza, acotadas a límites.

**Independent Test**: Evento alto + ocupación alta → sube y justifica; sugerido acotado a min/max; sin señal no propone; funciona sin mercado.

### Tests for User Story 2

- [ ] T010 [P] [US2] Tests de la heurística pura (evento+ocupación sube y justifica; acota a [min,max]; sin señal no cambia; sin mercado genera igual), en `apps/api/tests/test_suggestion_engine.py`

### Implementation for User Story 2

- [ ] T011 [US2] Heurística PURA `suggest_price` + `SuggestionInput/Output` en `apps/api/app/domain/suggestion.py`
- [ ] T012 [US2] `suggestion_engine.generate_suggestions` (por día: evento+ocupación+mercado → `PriceSuggestion(proposed)`; no re-propone equivalente) en `apps/api/app/services/suggestion_engine.py`

**Checkpoint**: sugerencias generadas y explicables.

---

## Phase 5: User Story 3 - Revisar, aprobar/rechazar y aplicar (Priority: P1)

**Goal**: Listar/aprobar/rechazar; aplicar reutiliza el motor de precios (003): audita origen=sugerencia y publica.

**Independent Test**: Aprobar+aplicar → precio cambia, auditado origen=sugerencia, publicado; rechazar → sin cambios; sin aprobar no se aplica.

### Tests for User Story 3

- [ ] T013 [P] [US3] Test: `apply_suggestion` audita origen=sugerencia + publica; reject no cambia; sin aplicar nada cambia, en `apps/api/tests/test_intelligence_service.py`

### Implementation for User Story 3

- [ ] T014 [US3] `intelligence_service.apply_suggestion` (vía `pricing_app_service`, origen=sugerencia; status=applied + enlace) y `approve`/`reject` (reusa `suggestion_service`) en `apps/api/app/services/intelligence_service.py`
- [ ] T015 [US3] Endpoints `GET /suggestions`, `POST /suggestions/{id}/approve|reject|apply` + registrar router en `apps/api/app/api/router.py`, en `apps/api/app/api/routes/suggestions.py`

**Checkpoint**: ciclo completo (sugerencia → precio publicado, auditado).

---

## Phase 6: User Story 4 - Referencia de mercado por ubicación (Priority: P2)

**Goal**: Baseline de mercado por zona que alimenta la heurística; opcional.

**Independent Test**: `BaselineMarket.get` devuelve la referencia de una zona; la heurística la considera; sin dato → genera igual.

### Tests for User Story 4

- [ ] T016 [P] [US4] Test: `BaselineMarket.get` devuelve referencia; la heurística la usa; `None` → genera igual, en `apps/api/tests/test_suggestion_engine.py`

### Implementation for User Story 4

- [ ] T017 [US4] `BaselineMarket` (lee la tabla `market_reference`) en `apps/api/app/market/reference.py`

**Checkpoint**: sugerencias informadas por mercado (cuando hay dato).

---

## Phase 7: User Story 5 - Escaneo programado diario (Priority: P2)

**Goal**: Job diario que escanea eventos+mercado y genera sugerencias, registrando la corrida; idempotente.

**Independent Test**: Ejecutar el escaneo → registra `IntelligenceRun` (conteos); 2ª corrida sin novedades no duplica.

### Tests for User Story 5

- [ ] T018 [P] [US5] Test: `scan` registra `IntelligenceRun` con conteos; 2ª corrida idempotente, en `apps/api/tests/test_intelligence_service.py`

### Implementation for User Story 5

- [ ] T019 [US5] `intelligence_service.scan` (orquesta scan_events + mercado + generate_suggestions; registra `IntelligenceRun`) en `apps/api/app/services/intelligence_service.py`
- [ ] T020 [US5] Entrypoint cron `scripts/scan_daily.py` en `apps/api/scripts/scan_daily.py`

**Checkpoint**: inteligencia fresca automáticamente.

---

## Phase 8: User Story 6 - Consultar sugerencias por el agente (Priority: P3)

**Goal**: El agente puede listar sugerencias vigentes (lectura).

**Independent Test**: Preguntar al agente por sugerencias de un período → responde con las reales.

### Tests for User Story 6

- [ ] T021 [P] [US6] Test: herramienta `get_suggestions` devuelve sugerencias reales (lectura), en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 6

- [ ] T022 [US6] Añadir herramienta de lectura `get_suggestions` al registro del agente en `apps/api/app/agent/tools.py`

**Checkpoint**: inteligencia accesible por chat.

---

## Phase 9: Polish & Cross-Cutting

- [ ] T023 [P] Añadir `SEARCH_BASE_URL` a config si falta y documentar endpoints `/suggestions` en `apps/api/README.md`
- [ ] T024 `uv run ruff check .` y `uv run pytest -q` en verde (apps/api)

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2: interfaces + modelos)** bloquea las historias.
- **US1 (P1, MVP)**: eventos (search + extracción).
- **US2 (P1)**: heurística + generación (usa eventos/ocupación).
- **US3 (P1)**: revisar/aplicar (usa 003 para publicar).
- **US4 (P2)**: mercado (mejora la heurística).
- **US5 (P2)**: escaneo programado (orquesta US1+US2).
- **US6 (P3)**: herramienta del agente.

### Dentro de cada historia
- Test primero (dobles) → interfaz/impl → servicio → endpoint.

### Paralelismo
- Foundational: T002, T003, T004 en paralelo (archivos distintos). Tests `[P]`. `intelligence_service.py`, `suggestion_engine.py`, `reference.py`, `tools.py` son secuenciales entre sí (mismo archivo).

---

## Implementation Strategy

### MVP primero (US1)
Setup → Foundational → US1 (eventos) → validar (dobles) → demo.

### Entrega incremental
US1 (eventos) → US2 (sugerencias) → US3 (aplicar) → US4 (mercado) → US5 (cron) → US6 (agente). Cada historia añade valor.

## Notes
- `[P]` = archivos distintos, sin dependencias pendientes.
- Dobles: `SearchProvider`/`MarketReference`/LLM/`ChannelManager` falsos → sin Tavily/OpenAI/Beds24 reales.
- Heurística PURA en `app/domain/suggestion.py`; aplicar usa `pricing_app_service` (003) → audita origen=sugerencia y publica.
- Reutiliza `Event`/`PriceSuggestion` y `event_service`/`suggestion_service` (001); nada duplicado.
