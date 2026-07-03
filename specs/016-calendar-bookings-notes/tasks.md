# Tasks: Detalle de reservas y notas del host en el calendario

**Input**: Design documents from `/specs/016-calendar-bookings-notes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/bookings-notes-api.md, quickstart.md

**Tests**: incluidos (Constitución IV: adaptador e import son frontera con el CM). Patrón: pytest + dobles; web `npm run build`.

**Organization**: por user story. Foundational = modelo/columna + migración.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable · **[Story]**: US1 (detalle al clic), US2 (import del nombre), US3 (notas CRUD), US4 (notas en calendario)

## Path Conventions

Monorepo: `apps/api/` (FastAPI) y `apps/web/` (Next.js), según plan.md.

---

## Phase 1: Foundational (bloqueante)

- [X] T001 Añadir `guest_name: Mapped[str | None]` (String(200), nullable) a `apps/api/app/models/booking.py` y clase `CalendarNote` (unit_type_id FK index, date_from/date_to Date NOT NULL, text String(500), TimestampMixin) a `apps/api/app/models/calendar.py`; exportar en `apps/api/app/models/__init__.py`
- [X] T002 Migración `apps/api/migrations/versions/d1e2f3a4b5c6_guest_name_calendar_note.py` (down_revision `c9d0e1f2a3b4`): `op.add_column('booking', ...)` + `op.create_table('calendar_note', ...)`; downgrade limpio (drop column + drop table)

**Checkpoint**: tests existentes verdes; `alembic heads` = un solo head.

---

## Phase 2: User Story 2 — Capturar el nombre del huésped (P1, habilitador del detalle)

**Goal**: puerto + adaptador V2 + import capturan/corrigen `guest_name`; V1 honesto (None).

**Independent Test**: import con dobles que reportan nombre → guardado; re-import corrige históricas; remoto vacío no borra.

- [X] T003 [US2] `apps/api/app/channels/base.py`: `RemoteBooking.guest_name: str | None = None`; `apps/api/app/channels/beds24_v2.py` (get_bookings): componer `f"{firstName} {lastName}".strip() or None` desde `b.get("firstName")`/`b.get("lastName")` (parciales OK)
- [X] T004 [US2] `apps/api/app/services/sync_service.py` (import_remote): al crear Booking → `guest_name=rb.guest_name`; en existente → si `rb.guest_name` no vacío y ≠ local, actualizar y contar en `updated` (mismo bloque del fix de channel_kind)
- [X] T005 [US2] Tests: extender `apps/api/tests/test_beds24_v2_channels.py` (o suite equivalente del adaptador) con firstName/lastName/parciales/vacío→None, y `apps/api/tests/test_sync_channels.py` con: crear con nombre, re-import corrige histórica sin nombre, remoto vacío NO borra nombre local

**Checkpoint**: el dato fluye del CM a la BD.

---

## Phase 3: User Story 1 — Detalle de reservas al clic (P1)

**Goal**: `GET /bookings` por rango + panel con huésped/canal/fechas/noches/estado/ref; día de salida no ocupa.

**Independent Test**: reserva ago 6-19 → aparece en clic de ago 6 y 18, NO en ago 19; sin nombre → "sin nombre".

- [X] T006 [US1] Crear `apps/api/app/api/routes/bookings.py`: `GET /bookings?unit_type_id&date_from&date_to` → confirmadas con `check_in <= date_to AND check_out > date_from`, orden check_in, respuesta del contrato (`nights=(check_out-check_in).days`, `channel=channel_kind.value`); registrar el router en `apps/api/app/api/router.py` (prefijo `/bookings`)
- [X] T007 [US1] Tests en `apps/api/tests/test_bookings_api.py` (cliente ASGITransport): solape del rango, cancelada excluida, nights, guest_name null, bordes (check_out == date_from no solapa)
- [X] T008 [P] [US1] Web: `BookingView` en `apps/web/lib/types.ts` + `api.listBookings(unitTypeId, from, to)` en `apps/web/lib/api.ts`
- [X] T009 [US1] Web: en `apps/web/app/(app)/calendar/page.tsx` query `["bookings", unitTypeId, from, to]`; helper noche `b.check_in <= d && d < b.check_out`; sección "Reservas" del nuevo `apps/web/components/calendar/day-info-panel.tsx` (huésped o "sin nombre", canal display, llegada → salida, noches, estado, ref) visible cuando la selección es un día con reservas

**Checkpoint**: "¿quién llega ese día?" respondido en un clic.

---

## Phase 4: User Story 3 — Notas del host (P1)

**Goal**: CRUD local de notas validado; cero llamadas al CM.

**Independent Test**: crear (día y rango), editar, borrar por API; 422 en inválidos; solapes permitidos.

- [X] T010 [US3] Crear `apps/api/app/services/calendar_note_service.py`: `CalendarNoteError`; list (por unit_type_id, orden date_from/id), create/update(parcial)/delete con validación (texto 1-500 tras strip, date_from <= date_to); LookupError si no existe
- [X] T011 [US3] Crear `apps/api/app/api/routes/calendar_notes.py`: `GET /calendar-notes?unit_type_id`, `POST`, `PATCH /{id}`, `DELETE /{id}` según contrato (422 CalendarNoteError, 404 LookupError); registrar router en `apps/api/app/api/router.py` (prefijo `/calendar-notes`)
- [X] T012 [US3] Tests en `apps/api/tests/test_calendar_notes.py`: CRUD completo, día único (from==to), solapes múltiples, 422 (vacío, 501 chars, fechas invertidas), 404
- [X] T013 [P] [US3] Web: `CalendarNote` en `apps/web/lib/types.ts` + `listCalendarNotes/createCalendarNote/updateCalendarNote/deleteCalendarNote` en `apps/web/lib/api.ts`

**Checkpoint**: la memoria del host tiene dónde vivir.

---

## Phase 5: User Story 4 — Notas visibles en el calendario (P2)

**Goal**: punto lima + leyenda en días con nota; sección "Notas" del panel (ver/crear sobre la selección/editar/borrar).

**Independent Test**: nota oct 19-21 → esos días marcados; panel muestra/edita; borrar quita el marcador; sin notas, render idéntico.

- [X] T014 [P] [US4] `apps/web/components/calendar/price-calendar.tsx`: prop opcional `noteDates?: Set<string>` → punto lima (`bg-lime-500`, title "Nota") + leyenda condicional "Nota" (patrón de las props 014/015)
- [X] T015 [US4] Completar `apps/web/components/calendar/day-info-panel.tsx` con la sección "Notas": lista de notas que cubren la selección (texto + rango) con editar inline (textarea) y borrar; formulario "Añadir nota" que crea sobre TODO el rango seleccionado (un día o arrastre); toasts con `detail`; invalidar `["calendar-notes"]`
- [X] T016 [US4] Integrar en `apps/web/app/(app)/calendar/page.tsx`: query `["calendar-notes", unitTypeId]`, `noteDates` del mes visible, prop al PriceCalendar y `DayInfoPanel` en la columna lateral (visible con cualquier selección; secciones internas condicionales)

**Checkpoint**: anotar → reencontrar cerrado.

---

## Phase 6: Polish & Cross-Cutting

- [X] T017 [P] Documentar en `docs/operations.md`: detalle de reservas al clic (privacidad del nombre: solo en la app, nunca en logs) y notas del host (locales, típicas para bloqueos)
- [X] T018 Verificación final: `cd apps/api && uv run pytest -q` + ruff; `cd apps/web && npm run build`; `alembic heads` único; revisar FR-010
- [ ] T019 Verificación EN VIVO tras merge (lectura/local, sin nada que revertir): re-import para poblar nombres (POST /sync/import), GET /bookings agosto con la reserva real y su huésped, clic en el calendario (panel), crear la nota real del bloqueo oct 19-21 (texto confirmado por el host) y verificar punto lima

---

## Dependencies & Execution Order

- **T001-T002** primero. **US2 (T003-T005)** después (usa la columna).
- **US1 (T006-T009)**: T006-T007 tras T001; T008 ∥ T006; T009 tras T006+T008 (y muestra nombres reales solo tras US2 — funcional sin ella con "sin nombre").
- **US3 (T010-T013)**: independiente de US1/US2 (solo necesita T001-T002); T013 ∥ T010-T012.
- **US4 (T014-T016)**: T014 ∥ T015 tras T013; T016 al final.
- **Polish** al cierre; T019 tras merge (requiere el texto de la nota real del host).

```
T001-T002 ─┬▶ T003-T005 (nombre) ─┐
           ├▶ T006-T009 (detalle) ─┼▶ T017-T018 ─▶ merge ─▶ T019
           └▶ T010-T013 (notas) ─▶ T014-T016 (UI notas) ─┘
```

## Implementation Strategy

**MVP = Foundational + US2 + US1** (el detalle con nombre es el valor principal). US3+US4 son el segundo incremento. Una rama/PR, commits por fase; T019 en prod tras el merge.
