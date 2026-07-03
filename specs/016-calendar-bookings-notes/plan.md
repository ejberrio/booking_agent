# Implementation Plan: Detalle de reservas y notas del host en el calendario

**Branch**: `016-calendar-bookings-notes` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-calendar-bookings-notes/spec.md`

## Summary

`RemoteBooking` gana `guest_name` (campo neutro; el adaptador V2 compone firstName+lastName — verificado en el OpenAPI oficial), `Booking` gana la columna y el import la captura/corrige en re-imports (patrón 012). Entidad nueva `CalendarNote` (unidad, rango, texto ≤500) con CRUD local sin fingerprint (criterio 015). Dos endpoints de lectura/gestión nuevos (`GET /bookings`, CRUD `/calendar-notes`) y el calendario integra ambos con el patrón client-side: marcador lima para notas, panel del día con reservas (huésped, canal, noches, referencia) y notas (crear desde la selección — incluye rangos —, editar, borrar). El endpoint de calendario NO se toca.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 + React 19 (web)
**Primary Dependencies**: FastAPI + SQLAlchemy 2.0 async + Alembic; react-query + sonner
**Storage**: PostgreSQL / SQLite tests. **UNA migración** (`d1e2f3a4b5c6`, down `c9d0e1f2a3b4`): columna `booking.guest_name` + tabla `calendar_note`.
**Testing**: pytest (dobles); web `npm run build`
**Target Platform**: Railway (CD a main)
**Project Type**: monorepo web application
**Performance Goals**: n/a (decenas de reservas/notas)
**Constraints**: guest_name solo se muestra en la app (nunca en logs — el middleware ya loguea solo method/path/status); notas 100% locales; no romper 199 tests; sin datos nuevos, render idéntico
**Scale/Scope**: single-tenant; ~7 archivos API + ~5 web + 1 migración

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; sin ADR (patrones ya establecidos en 014/015) |
| II. Provider-agnostic | ✅ `guest_name` es campo neutro del puerto (el V2 compone firstName+lastName; V1 lo deja None); nada propietario en el dominio |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ cero escrituras al canal en toda la feature: lecturas de reservas + notas locales (mismo criterio que el registro de deals 015) |
| IV. Tipado y pruebas | ✅ tests de import (captura/corrección de nombre), noche [in, out), CRUD de notas con validación |
| V. Simplicidad | ✅ una columna + una tabla plana; merge client-side; sin abstracciones nuevas |

**Post-diseño (re-check)**: ✅ sin violaciones. Privacidad (FR-003): dato personal mostrado solo en la app single-tenant; el logging existente no toca cuerpos de respuesta.

## Project Structure

### Documentation (this feature)

```text
specs/016-calendar-bookings-notes/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/bookings-notes-api.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/api/
├── app/channels/base.py                    # RemoteBooking += guest_name
├── app/channels/beds24_v2.py               # compone firstName+lastName
├── app/models/booking.py                   # + guest_name (String(200) nullable)
├── app/models/calendar.py                  # + CalendarNote
├── migrations/versions/d1e2f3a4b5c6_guest_name_calendar_note.py
├── app/services/sync_service.py            # import captura/corrige guest_name
├── app/services/calendar_note_service.py   # NUEVO: CRUD validado
├── app/api/routes/bookings.py              # NUEVO: GET /bookings (rango)
├── app/api/routes/calendar_notes.py        # NUEVO: CRUD /calendar-notes
├── app/api/routes/__init__.py              # registrar routers
└── tests/test_calendar_notes.py + test_sync_guest_name.py (o extensión de suites)

apps/web/
├── components/calendar/price-calendar.tsx  # + prop noteDates (punto lima + leyenda)
├── components/calendar/day-info-panel.tsx  # NUEVO: reservas del día + notas (CRUD)
├── app/(app)/calendar/page.tsx             # queries bookings+notes; panel; prop
└── lib/{types,api}.ts                      # BookingView, CalendarNote + funciones
```

**Structure Decision**: monorepo existente; módulos nuevos pequeños y planos.

## Decisiones clave (detalle en research.md)

1. **`guest_name` como campo único neutro del puerto** — el adaptador compone nombre+apellido; V1 legacy devuelve None (honesto). Import: set al crear; en re-import corrige si el remoto trae nombre distinto/nuevo (nunca borra un nombre local con un remoto vacío).
2. **`GET /bookings?unit_type_id&date_from&date_to`** — reservas CONFIRMADAS cuya estancia solapa el rango (noches [check_in, check_out)); respuesta con `nights` calculado. Router nuevo `bookings.py`.
3. **`CalendarNote` plano + CRUD sin fingerprint** — texto ≤500, rango coherente (día único = from==to); DELETE real; nunca toca el CM (criterio del registro de deals 015).
4. **UI en un solo panel nuevo (`DayInfoPanel`)** — al seleccionar en el calendario: sección "Reservas" (solo si la selección es un día con reservas: huésped o "sin nombre", canal display, llegada → salida, noches, estado, ref) y sección "Notas" (notas que cubren el día/rango seleccionado + formulario para crear sobre TODA la selección — un día o un rango por arrastre — + editar/borrar). Marcador lima (`bg-lime-500`) para días con nota; las reservas ya tienen su punto rojo (no se duplica marcador).
5. **Privacidad del nombre** — solo viaja API→web autenticada; el middleware de logging registra `method/path/status` sin query ni body; el serializador del agente (`get_bookings` tool) NO gana el nombre en esta feature (el chat no lo necesita; menos superficie para un dato personal).

## Fase 0 → research.md · Fase 1 → data-model.md, contracts/, quickstart.md

Sin NEEDS CLARIFICATION: el OpenAPI oficial confirma `firstName`/`lastName` en el schema de booking; el resto son patrones ya validados en 012/014/015.
