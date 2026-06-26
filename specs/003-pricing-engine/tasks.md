---
description: "Task list — Motor de precios"
---

# Tasks: Motor de precios

**Input**: Design documents from `specs/003-pricing-engine/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pricing-api.md

**Tests**: INCLUIDOS (constitución IV). Publicación con **ChannelManager falso** (sin API real).

**Organización**: por historia de usuario (US1–US5). Trabajo en `apps/api`. Reutiliza dominio/servicios de 001 y el conector de 002.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivo distinto, sin dependencias pendientes.
- **[Story]**: US1–US5.

---

## Phase 1: Setup

- [ ] T001 [P] Crear paquete `app/schemas/` (con `__init__.py`) en `apps/api/app/`

---

## Phase 2: Foundational (objetos de valor + publicación del efectivo)

**⚠️ Bloqueante para todas las historias.**

- [ ] T002 Objetos de valor en `apps/api/app/schemas/pricing.py`: `RangeSelection` (con expansión a fechas: rango + weekdays + days), `CalendarDayView`, `ChangePreviewDay`, `ChangePreview` (con `fingerprint`), `ApplyResult`
- [ ] T003 Helper `publish_effective` en `apps/api/app/services/pricing_app_service.py`: calcula el efectivo por día (dominio 001), agrupa días contiguos con igual efectivo y publica vía el puerto `ChannelManager`, registrando incidencias (reusa `sync_service`/`channels`)

**Checkpoint**: base lista (objetos de valor + publicación del efectivo).

---

## Phase 3: User Story 1 - Consultar precios y calendario (Priority: P1) 🎯 MVP

**Goal**: Ver, por día/rango, precio base, efectivo, disponibilidad y promociones vigentes.

**Independent Test**: `GET /pricing/calendar` devuelve por día base, efectivo, disponibilidad y promos.

### Tests for User Story 1

- [ ] T004 [P] [US1] Test `get_calendar` (base + efectivo + disponibilidad + promos) en `apps/api/tests/test_pricing_app.py`

### Implementation for User Story 1

- [ ] T005 [US1] `get_calendar()` (usa `effective_price`/promos del dominio 001) en `apps/api/app/services/pricing_app_service.py`
- [ ] T006 [US1] Endpoint `GET /pricing/calendar` + `get_adapter()` + registrar router en `apps/api/app/api/router.py`, en `apps/api/app/api/routes/pricing.py`

**Checkpoint**: consulta de precios funcional (MVP).

---

## Phase 4: User Story 2 - Asignar precio a un día (Priority: P1)

**Goal**: Fijar el precio de un día: validar límites, auditar y publicar el efectivo.

**Independent Test**: Fijar un precio válido (audita + publica) y uno fuera de límites (rechazado).

### Tests for User Story 2

- [ ] T007 [P] [US2] Test `set_day_price`: fuera de límites rechazado; válido audita + publica efectivo en `apps/api/tests/test_pricing_app.py`

### Implementation for User Story 2

- [ ] T008 [US2] `set_day_price()` (valida regla → `pricing_service.set_base_price` → `publish_effective`) en `apps/api/app/services/pricing_app_service.py`
- [ ] T009 [US2] Endpoint `POST /pricing/day` en `apps/api/app/api/routes/pricing.py`

**Checkpoint**: cambios de precio por día auditados y publicados.

---

## Phase 5: User Story 3 - Asignar precio por rangos con previsualización (Priority: P1)

**Goal**: Cambiar precios por rango (con filtro día-semana/grupos), previsualizar el diff y confirmar; días inválidos excluidos; preview obsoleto bloqueado.

**Independent Test**: Previsualizar un rango filtrando viernes/sábados, ver el diff y los inválidos, confirmar y verificar que solo se aplicaron los válidos; un preview obsoleto responde `stale`.

### Tests for User Story 3

- [ ] T010 [P] [US3] Tests de rango (preview con filtro de día-semana + inválidos marcados; apply aplica válidos/excluye inválidos; preview obsoleto → `stale`) en `apps/api/tests/test_pricing_app.py`

### Implementation for User Story 3

- [ ] T011 [US3] `preview_range()` (expande `RangeSelection`, calcula old/new/valid por día, `fingerprint`) en `apps/api/app/services/pricing_app_service.py`
- [ ] T012 [US3] `apply_range()` (detecta `fingerprint` obsoleto → `stale`; aplica solo válidos: `set_base_price` + `publish_effective`) en `apps/api/app/services/pricing_app_service.py`
- [ ] T013 [US3] Endpoints `POST /pricing/range/preview` y `POST /pricing/range/apply` en `apps/api/app/api/routes/pricing.py`

**Checkpoint**: gestión por rangos con preview/confirmación.

---

## Phase 6: User Story 4 - Gestionar promociones (Priority: P2)

**Goal**: CRUD de promociones; auditar el cambio y recalcular/re-publicar el efectivo de los días afectados.

**Independent Test**: Crear una promo (baja el efectivo + re-publica + queda auditada); solapar dos y verificar que gana la de mayor descuento; eliminar y ver que el efectivo vuelve al base.

### Tests for User Story 4

- [ ] T014 [P] [US4] Tests: crear promo audita (`PromotionChangeLog`) + re-publica efectivo; promos solapadas → mayor descuento en `apps/api/tests/test_promotion_service.py`

### Implementation for User Story 4

- [ ] T015 [P] [US4] Modelo `PromotionChangeLog` en `apps/api/app/models/audit.py` + enum `PromotionAction` en `apps/api/app/models/enums.py` (registrar en `app/models/__init__.py`)
- [ ] T016 [US4] `promotion_service` (create/update/delete: audita en `PromotionChangeLog` + recalcula + `publish_effective` de días afectados) en `apps/api/app/services/promotion_service.py`
- [ ] T017 [US4] Endpoints CRUD `POST/PUT/DELETE /pricing/promotions` en `apps/api/app/api/routes/pricing.py`
- [ ] T018 [US4] Migración Alembic para `promotion_change_log` en `apps/api/migrations/versions/`

**Checkpoint**: promociones gestionadas, auditadas y reflejadas en Booking.

---

## Phase 7: User Story 5 - Auditoría y rollback (Priority: P2)

**Goal**: Ver el historial de cambios y revertir (con conflicto si hay cambios posteriores), re-publicando el efectivo.

**Independent Test**: Cambiar un precio, ver su historial, revertirlo (vuelve al anterior y re-publica) y provocar un conflicto que exige confirmación.

### Tests for User Story 5

- [ ] T019 [P] [US5] Test `rollback_and_publish`: revierte y publica; conflicto (cambios posteriores) exige `confirm` en `apps/api/tests/test_pricing_app.py`

### Implementation for User Story 5

- [ ] T020 [US5] `rollback_and_publish()` (usa `audit_service.rollback_change` → `publish_effective`) y `history()` en `apps/api/app/services/pricing_app_service.py`
- [ ] T021 [US5] Endpoints `POST /pricing/rollback` y `GET /pricing/history` en `apps/api/app/api/routes/pricing.py`

**Checkpoint**: control total (historial + revertir) con publicación.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T022 [P] Documentar los endpoints `/pricing/*` en `apps/api/README.md`
- [ ] T023 `uv run ruff check .` y `uv run pytest -q` en verde (apps/api)

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2: objetos de valor + publish_effective)** bloquea las historias.
- **US1 (P1, MVP)**: consulta (base + efectivo).
- **US2 (P1)**: asignar día (usa publish_effective).
- **US3 (P1)**: rango + preview (usa validación y publish_effective).
- **US4 (P2)**: promociones (nueva tabla + re-publicación).
- **US5 (P2)**: rollback (usa audit_service 001 + publish_effective).

### Dentro de cada historia
- Tests primero → servicio → endpoint (→ modelo/migración en US4).

### Paralelismo
- Tests `[P]` (archivos de test) y el modelo `PromotionChangeLog` (`audit.py`) en paralelo con el servicio. Las funciones de `pricing_app_service.py` y los endpoints de `routes/pricing.py` son secuenciales (mismo archivo).

---

## Implementation Strategy

### MVP primero (US1)
Setup → Foundational → US1 (consultar precios) → validar → demo.

### Entrega incremental
US1 (consultar) → US2 (día) → US3 (rango+preview) → US4 (promos) → US5 (rollback). Cada historia añade valor sin romper las anteriores.

## Notes
- `[P]` = archivos distintos, sin dependencias pendientes.
- Reutiliza `pricing_service`/`audit_service` (001), el dominio (`effective_price`/`best_promotion`/`violates_rule`) y el conector (002). Nada de lógica duplicada.
- Publicación siempre del **precio efectivo** vía el puerto `ChannelManager` (falso en tests).
- Toda escritura: validar → auditar → publicar; rango/bulk con preview + confirmación.
