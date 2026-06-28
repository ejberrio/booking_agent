---
description: "Task list — Gestión de disponibilidad (bloquear/abrir fechas)"
---

# Tasks: Gestión de disponibilidad (bloquear/abrir fechas)

**Input**: Design documents from `/specs/008-availability-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Se incluyen tests en los límites que pueden costar dinero/reputación (Constitución IV): servicio de disponibilidad (omitir reservas, idempotencia, publicación resiliente), adapter y agente.

**Organization**: por historia — US1 (bloquear por chat, P1), US2 (reabrir por chat, P1), US3 (calendario, P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivos distintos, sin dependencias.
- Monorepo: `apps/api/`, `apps/web/`.

---

## Phase 1: Setup

- [X] T001 [P] Definir DTOs de disponibilidad (`AvailabilityDayView` con date/old_available/new_available/valid/skip_reason, y `AvailabilityPreview` con affected_count/skipped_count/reinforced/fingerprint) en `apps/api/app/schemas/pricing.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Plumbing compartido por chat y calendario: modelo de auditoría, escritura de disponibilidad en el puerto/adaptador, servicio de bloqueo/apertura y publicación. **Bloquea todas las historias.**

- [X] T002 Crear modelo `AvailabilityChangeLog` (unit_type_id, date, old_units_available, new_units_available, was_blocked, is_blocked, origin: ChangeOrigin, TimestampMixin) en `apps/api/app/models/availability.py` e importarlo en `apps/api/app/models/__init__.py`
- [X] T003 Generar y revisar la migración Alembic de `availability_change_log` en `apps/api/migrations/versions/` (añadir `from sqlalchemy import Text` si la autogeneración lo requiere)
- [X] T004 Añadir `set_availability_range(room_external_id, date_from, date_to, num_avail) -> WriteResult` al puerto `ChannelManager` en `apps/api/app/channels/base.py`
- [X] T005 Implementar `set_availability_range` en `apps/api/app/channels/beds24_v2.py` (`POST /inventory/rooms/calendar` con `numAvail`; verificación por relectura con get_rates)
- [X] T006 [P] Implementar `set_availability_range` en `apps/api/app/channels/beds24.py` → lanza `ChannelError` ("V1 no soporta escritura")
- [X] T007 [P] Test del adapter V2 `set_availability_range` (éxito verificado + no verificado) en `apps/api/tests/test_beds24_v2_adapter.py`
- [X] T008 Implementar `availability_service` (preview + apply para `block`/`open`: por noche del rango con filtro weekdays, OMITE noches con reserva confirmada, idempotente, escribe CalendarDay y `AvailabilityChangeLog`) en `apps/api/app/services/availability_service.py`
- [X] T009 Añadir `publish_availability` en `apps/api/app/services/sync_service.py` (calca `publish_price`: captura `ChannelError` → `SyncIssue`; conserva cambio local)
- [X] T010 Exponer `is_blocked` por día: ampliar `CalendarDayView` en `apps/api/app/schemas/pricing.py` y `get_calendar` en `apps/api/app/services/pricing_app_service.py` (y el serializado en `apps/api/app/api/routes/pricing.py`)
- [X] T011 [P] Tests de `availability_service` en `apps/api/tests/test_availability_service.py` (bloquear omite noche reservada; abrir no toca reservada; idempotencia; publicación resiliente registra incidencia; audita 1 log por noche)

**Checkpoint**: el servicio bloquea/abre por rango, respeta reservas, publica a Beds24 y audita.

---

## Phase 3: User Story 1 - Bloquear fechas por chat (Priority: P1) 🎯 MVP

**Goal**: El host cierra fechas por chat (propone→confirma), omitiendo reservas, publicado a Beds24.

**Independent Test**: "cierra del 1 al 3 de julio" → propuesta de bloqueo → confirmar → noches cerradas (app + Beds24); una noche reservada del rango se omite.

- [X] T012 [US1] Añadir herramienta de escritura `propose_block_availability` (unit_type_id, date_from, date_to, weekdays?) en `apps/api/app/agent/tools.py` y su manejo en `build_proposal`/`apply_proposal` (preview con afectadas/omitidas; aplica vía `availability_service` con origin=chat)
- [X] T013 [US1] Actualizar `apps/api/app/agent/prompts.py`: añadir la capacidad de bloquear disponibilidad y QUITAR la regla "no puedes cambiar disponibilidad"; ante solicitudes de disponibilidad usar la tool (nunca precio)
- [X] T014 [US1] Test del flujo de bloqueo por chat en `apps/api/tests/test_agent_orchestrator.py` (propone→confirma→bloquea; omite reserva)

**Checkpoint**: bloquear por chat funciona de punta a punta.

---

## Phase 4: User Story 2 - Reabrir fechas por chat (Priority: P1)

**Goal**: El host reabre fechas previamente bloqueadas por chat (operación inversa), sin alterar reservas.

**Independent Test**: tras bloquear, "vuelve a abrir el 2 de julio" → propuesta de apertura → confirmar → disponible de nuevo (app + Beds24); una noche reservada no se reabre.

- [X] T015 [US2] Añadir herramienta `propose_open_availability` en `apps/api/app/agent/tools.py` y su manejo en `build_proposal`/`apply_proposal` (reutiliza `availability_service` con action=open)
- [X] T016 [US2] Test del flujo de reapertura por chat en `apps/api/tests/test_agent_orchestrator.py` (propone→confirma→abre; no toca reservada)

**Checkpoint**: bloquear + reabrir por chat funcionan (MVP completo).

---

## Phase 5: User Story 3 - Bloquear/abrir desde el calendario (Priority: P2)

**Goal**: Gestión visual en el calendario: seleccionar rango, bloquear/abrir con preview→confirmar, estados visibles.

**Independent Test**: seleccionar un rango → Bloquear → preview (afectadas/omitidas) → Confirmar → noches marcadas como bloqueadas; repetir con Abrir; estados distinguibles.

- [X] T017 [US3] Endpoints `POST /pricing/availability/preview` y `POST /pricing/availability/apply` (con fingerprint/stale) en `apps/api/app/api/routes/pricing.py`, usando `availability_service`
- [X] T018 [P] [US3] Cliente y tipos en `apps/web/lib/api.ts` (`availabilityPreview`, `availabilityApply`) y `apps/web/lib/types.ts` (`is_blocked`, vistas de preview/estado)
- [X] T019 [US3] Estados visuales por día en `apps/web/components/calendar/price-calendar.tsx` (disponible / reservada / bloqueada / sin datos)
- [X] T020 [US3] Acciones Bloquear/Abrir con preview→confirmar en `apps/web/components/calendar/range-editor.tsx`
- [X] T021 [US3] Integrar acciones en `apps/web/app/(app)/calendar/page.tsx` y dejar `npm run build` verde

**Checkpoint**: gestión de disponibilidad visual completa.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T022 [P] Actualizar `docs/operations.md` con la nueva capacidad (bloquear/abrir) si aplica
- [X] T023 Ejecutar `uv run ruff check .` + `uv run pytest` (api) y `npm run build` (web) — todo verde
- [X] T024 Validar `quickstart.md` (chat bloquear/abrir, calendario, y verificación de que las reservas no se rompen)

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; **bloquea** US1/US2/US3. Orden interno: T002→T003 (modelo→migración); T004→T005/T006 (puerto→adaptadores); T008 usa T002/T005/T009; T010 independiente.
- **US1 (Phase 3)** y **US2 (Phase 4)**: dependen de Foundational; comparten `availability_service`. US2 reutiliza el manejo de US1 (la apertura es simétrica).
- **US3 (Phase 5)**: depende de Foundational (servicio + is_blocked en calendario); independiente de US1/US2 (usa los endpoints REST, no el agente).
- **Polish (Phase 6)**: al final.

## Parallel Opportunities

- Setup: T001.
- Foundational: T006 ‖ T007 ‖ T011 (archivos distintos) una vez listo lo que dependen.
- Tras Foundational, **US1/US2 (chat)** y **US3 (calendario)** pueden avanzar en paralelo (backend agente vs endpoints+frontend).
- US3: T018 (cliente/tipos) en paralelo con tareas de backend del endpoint.

## Implementation Strategy

### MVP (gestión por chat)
1. Setup + Foundational.
2. US1 (bloquear) + US2 (reabrir) por chat → **valor central entregado**.
3. Validar: cerrar/reabrir por chat, reservas intactas, publicado a Beds24.

### Incremental
4. US3 (calendario) → gestión visual.
5. Polish → tests/build verdes + validación del quickstart.

## Notes

- `[P]` = archivos distintos, sin dependencias.
- Constitución III: bloquear/abrir SIEMPRE propone→confirma (nunca automático).
- Constitución IV: tests de servicio (omitir reservas, idempotencia, resiliencia), adapter y agente.
- Nunca alterar noches con reserva confirmada (cero overbooking).
