---
description: "Task list — Conector de Channel Manager (Beds24)"
---

# Tasks: Conector de Channel Manager (Beds24)

**Input**: Design documents from `specs/002-beds24-connector/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUIDOS (HTTP mockeado con `httpx.MockTransport`; sin API real ni secretos). La constitución (IV) exige pruebas para integraciones.

**Organización**: por historia de usuario (US1–US5). Trabajo en `apps/api`. Reutiliza modelos/servicios de la feature 001.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivo distinto, sin dependencias pendientes.
- **[Story]**: US1–US5.

---

## Phase 1: Setup

- [ ] T001 Crear paquete `app/channels/` (con `__init__.py`) y añadir `BEDS24_API_KEY`, `BEDS24_PROP_ID`, `BEDS24_ROOM_ID`, `BEDS24_BASE_URL` a `apps/api/app/core/config.py`
- [ ] T002 [P] Añadir fixtures de `httpx.MockTransport` (respuestas V1 de ejemplo + helper para construir AsyncClient mockeado) en `apps/api/tests/conftest.py`

---

## Phase 2: Foundational (puerto provider-agnostic)

**⚠️ Bloqueante para todas las historias.**

- [ ] T003 [P] DTOs neutrales (`RemoteProperty`, `RemoteRoom`, `RemoteRate`, `RemoteBooking`, `WriteResult`, `ConnectionInfo`) y `Protocol` `ChannelManager` en `apps/api/app/channels/base.py`
- [ ] T004 [P] Excepciones tipadas (`ChannelError`, `AuthError`, `RateLimited`, `WriteUnverified`) en `apps/api/app/channels/errors.py`
- [ ] T005 Base del adaptador Beds24: `AsyncClient` httpx, inyección de `apiKey` desde settings, helper `_request` con mapeo de errores y backoff, en `apps/api/app/channels/beds24.py` (depende de T003, T004)

**Checkpoint**: puerto y cliente base listos.

---

## Phase 3: User Story 1 - Conectar y validar la conexión (Priority: P1) 🎯 MVP

**Goal**: Probar la conexión con Beds24 y listar las propiedades de la cuenta; persistir el estado de la conexión.

**Independent Test**: `POST /sync/test` con credenciales válidas confirma acceso y lista propiedades; con inválidas, error claro sin exponer secretos.

### Tests for User Story 1

- [ ] T006 [P] [US1] Test: `test_connection` OK lista propiedades y credenciales inválidas → `AuthError`; la apiKey no aparece en el error, en `apps/api/tests/test_beds24_adapter.py`

### Implementation for User Story 1

- [ ] T007 [US1] Implementar `Beds24Adapter.get_properties` y `test_connection` (parseo de `getProperties` → DTOs) en `apps/api/app/channels/beds24.py` (depende de T005)
- [ ] T008 [P] [US1] Modelo `ChannelManagerConnection` en `apps/api/app/models/sync.py` (registrar en `app/models/__init__.py`)
- [ ] T009 [US1] `sync_service.test_connection()`: ejecuta la prueba, persiste estado y `last_verified_at` en `apps/api/app/services/sync_service.py` (depende de T007, T008)
- [ ] T010 [US1] Endpoint `POST /sync/test` y registrar el router en `apps/api/app/api/router.py`, en `apps/api/app/api/routes/sync.py`
- [ ] T011 [US1] Migración Alembic para `channel_manager_connection` en `apps/api/migrations/versions/`

**Checkpoint**: se puede probar la conexión y ver el estado (MVP).

---

## Phase 4: User Story 2 - Importar datos (lectura) (Priority: P1)

**Goal**: Traer propiedades, unidades, calendario/disponibilidad, precios y reservas al modelo local, incremental y sin duplicar; baseline sin auditar.

**Independent Test**: `POST /sync/import` puebla el modelo local con `external_ref`; re-ejecutar no duplica.

### Tests for User Story 2

- [ ] T012 [P] [US2] Test: `get_rates` y `get_bookings` mapean a DTOs (mock), en `apps/api/tests/test_beds24_adapter.py`
- [ ] T013 [P] [US2] Test: `import_remote` hace upsert sin crear `PriceChangeLog` y es idempotente (segunda corrida sin duplicar), en `apps/api/tests/test_sync_service.py`

### Implementation for User Story 2

- [ ] T014 [US2] `Beds24Adapter.get_rates` y `get_bookings` (parseo `getRoomDates`/`getBookings`) en `apps/api/app/channels/beds24.py`
- [ ] T015 [P] [US2] Modelos `SyncRun` y `SyncIssue` en `apps/api/app/models/sync.py`
- [ ] T016 [US2] `sync_service.import_remote()`: mapear DTOs → upsert `Property/UnitType/CalendarDay/Rate/Booking` (con `external_ref`), baseline sin auditar, cursor incremental; registrar `SyncRun(import)` en `apps/api/app/services/sync_service.py` (depende de T014, T015)
- [ ] T017 [US2] Endpoints `POST /sync/import` y `GET /sync/runs` en `apps/api/app/api/routes/sync.py`
- [ ] T018 [US2] Migración Alembic para `sync_run`, `sync_issue` en `apps/api/migrations/versions/`

**Checkpoint**: el estado real (precios/disponibilidad/reservas) se ve en local.

---

## Phase 5: User Story 3 - Publicar precios (escritura) con verificación y auditoría (Priority: P1)

**Goal**: Enviar precios por día/rango a Beds24, verificar releyendo y dejar la auditoría local; idempotente y con rate limiting.

**Independent Test**: Fijar un precio local y `POST /sync/publish`; el remoto refleja el valor (verificado) y hay entrada de auditoría.

### Tests for User Story 3

- [ ] T019 [P] [US3] Test: `set_rate`/`set_rate_range` releen y marcan `verified=True`; escritura no reflejada → `verified=False` (mock), en `apps/api/tests/test_beds24_adapter.py`
- [ ] T020 [P] [US3] Test: `publish_price` con `verified=False` abre `SyncIssue(write_unverified)`, en `apps/api/tests/test_sync_service.py`

### Implementation for User Story 3

- [ ] T021 [US3] `Beds24Adapter.set_rate` y `set_rate_range` (`setRoomDates` + relectura de verificación) en `apps/api/app/channels/beds24.py`
- [ ] T022 [US3] `sync_service.publish_price()`: publica el precio local (ya auditado por `pricing_service`), abre `SyncIssue` si no se verifica; registrar `SyncRun(publish)` en `apps/api/app/services/sync_service.py`
- [ ] T023 [US3] Endpoint `POST /sync/publish` en `apps/api/app/api/routes/sync.py`

**Checkpoint**: los precios fijados llegan a Beds24 (y a Booking), verificados y auditados.

---

## Phase 6: User Story 4 - Reconciliación y manejo de errores (Priority: P2)

**Goal**: Detectar discrepancias (sin sobrescribir), reflejar reservas/disponibilidad remotas y registrar errores; respetar rate limits.

**Independent Test**: Provocar precio distinto local vs remoto → `SyncIssue(price_discrepancy)` sin overwrite; provocar error de comunicación → queda registrado.

### Tests for User Story 4

- [ ] T024 [P] [US4] Test: discrepancia de precio abre `SyncIssue` sin modificar `Rate` local; reserva remota actualiza disponibilidad, en `apps/api/tests/test_sync_service.py`
- [ ] T025 [P] [US4] Test: rate limit → backoff/`RateLimited`; error de comunicación → `SyncIssue(comm_error)`; sin secretos en el detalle, en `apps/api/tests/test_beds24_adapter.py`

### Implementation for User Story 4

- [ ] T026 [US4] `sync_service.reconcile()`: discrepancias de precio → `SyncIssue` (sin overwrite); reservas/disponibilidad remotas → local, en `apps/api/app/services/sync_service.py`
- [ ] T027 [US4] Rate limiting con backoff y redacción de secretos en el manejo de errores en `apps/api/app/channels/beds24.py`
- [ ] T028 [US4] Endpoint `GET /sync/issues` (listar incidencias abiertas) en `apps/api/app/api/routes/sync.py`

**Checkpoint**: robustez y confianza (cero sobrescrituras silenciosas; errores visibles).

---

## Phase 7: User Story 5 - Sincronización programada y manual (Priority: P3)

**Goal**: Sincronización diaria por cron y disparo manual; incremental.

**Independent Test**: Ejecutar `scripts/sync_daily.py` y verificar que corre import+reconcile, registra `SyncRun` y procesa solo lo cambiado.

### Tests for User Story 5

- [ ] T029 [P] [US5] Test: segunda corrida incremental no duplica y usa el cursor de la corrida previa, en `apps/api/tests/test_sync_service.py`

### Implementation for User Story 5

- [ ] T030 [US5] Entrypoint para cron `scripts/sync_daily.py` (import + reconcile, registra `SyncRun`) en `apps/api/scripts/sync_daily.py`

**Checkpoint**: datos frescos automáticamente; re-sync manual disponible.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T031 [P] Añadir variables `BEDS24_*` (sin valores secretos) a `.env.example` y documentar en `apps/api/README.md`
- [ ] T032 [P] Ejecutar validación de `specs/002-beds24-connector/quickstart.md` (con mocks) y alinear `data-model.md` si hubo ajustes
- [ ] T033 `uv run ruff check .` y `uv run pytest -q` en verde (apps/api)

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2: puerto + cliente base)** bloquea las historias.
- **US1 (P1, MVP)**: conexión + `get_properties` (reutilizado por US2).
- **US2 (P1)**: lectura/import (usa adaptador de US1 + nuevos métodos).
- **US3 (P1)**: escritura (usa `pricing_service` de 001 para auditar).
- **US4 (P2)**: reconciliación/errores (sobre import/publish).
- **US5 (P3)**: cron sobre import+reconcile.

### Dentro de cada historia
- Tests primero (mock) → métodos del adaptador → modelos → servicio → endpoint → migración.

### Paralelismo
- Setup: T002 [P]. Foundational: T003, T004 [P].
- Por historia, los tests `[P]` y los modelos/archivos distintos `[P]` van en paralelo (p. ej. T008/T015 en `sync.py` vs adaptador en `beds24.py`).

---

## Implementation Strategy

### MVP primero (US1)
Setup → Foundational → US1 (probar conexión y listar propiedades) → validar → demo.

### Entrega incremental
US1 (conexión) → US2 (import) → US3 (publicar) → US4 (reconciliación) → US5 (cron). Cada historia añade valor sin romper las anteriores.

## Notes
- `[P]` = archivos distintos, sin dependencias pendientes.
- Cada modelo nuevo se registra en `app/models/__init__.py` (autogenerate Alembic).
- Tests con `httpx.MockTransport`: **sin** llamadas a la API real ni credenciales reales.
- Las escrituras de precio se auditan vía `pricing_service` (feature 001); el conector solo publica y verifica.
- Secretos solo desde env; nunca en logs ni en `SyncIssue.detail`.
