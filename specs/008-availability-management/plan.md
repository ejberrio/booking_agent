# Implementation Plan: Gestión de disponibilidad (bloquear/abrir fechas)

**Branch**: `008-availability-management` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-availability-management/spec.md`

## Summary

Permitir al host **bloquear (cerrar)** y **abrir (reabrir)** noches o rangos de su unidad, desde el **chat** y desde el **calendario** de la web, publicando a Booking vía Beds24 V2 (`numAvail`). Reutiliza el patrón ya existente para precios: **propone → el host confirma → se aplica y publica → se audita**, con publicación resiliente (incidencia si falla). **Nunca toca noches con reserva confirmada** (cero overbooking). La reversión es la operación inversa (abrir deshace bloquear).

## Technical Context

**Language/Version**: Python (apps/api, `uv`) + TypeScript/Next.js 15 (apps/web)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 async, Alembic, httpx (api); Next.js App Router, @tanstack/react-query (web)
**Storage**: PostgreSQL (Neon en prod); modelos `CalendarDay` (units_available, is_blocked), `Booking`
**Testing**: pytest (api, dobles: FakeChannelManager, SQLite async), `npm run build` (web)
**Target Platform**: Railway (web+api) + Neon; ya en producción
**Project Type**: web (monorepo apps/web + apps/api)
**Performance Goals**: single-tenant, baja concurrencia
**Constraints**: reutilizar el flujo propone→confirma→publica→audita; no romper reservas; secretos solo por entorno
**Scale/Scope**: 1 host, 1 unidad; rangos de hasta ~1 año

## Constitution Check

| Principio | Cumplimiento |
|-----------|--------------|
| **I. Spec-Driven** | Feature creada por specify→clarify→plan→tasks→implement. ✅ |
| **II. Provider-agnostic** | Se añade `set_availability_range` al **puerto** `ChannelManager` (no a Beds24 directamente); el dominio no conoce el proveedor. V2 implementa; V1 lanza error (sus escrituras están muertas). ✅ |
| **III. Human-in-the-loop (NO NEGOCIABLE)** | Bloquear/abrir SIEMPRE pasan por propuesta + confirmación del host (AgentAction / preview→confirmar en UI), auditado y reversible (operación inversa). El cron/escaneo no toca disponibilidad. ✅ |
| **IV. Tipado y pruebas en los límites** | Tests para: `availability_service` (omitir noches reservadas, idempotencia, publicación resiliente), adapter `set_availability_range`, y herramientas del agente. Tipado Pydantic/TS. ✅ |
| **V. Simplicidad (single-tenant, YAGNI)** | Reutiliza CalendarDay (ya tiene is_blocked/units_available) y el patrón de precios. Una tabla nueva de auditoría (`AvailabilityChangeLog`) y un servicio. Sin colas ni abstracciones nuevas. ✅ |
| **Restricciones técnicas** | Secretos solo por entorno; sin credenciales en repo/logs; disponibilidad cifrada en tránsito (Beds24 V2). ✅ |

**Resultado**: PASS, sin violaciones (Complexity Tracking vacío).

## Project Structure

### Documentation (this feature)

```text
specs/008-availability-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── availability-api.md      # endpoints preview/apply de disponibilidad
│   ├── agent-tools.md           # propose_block_availability / propose_open_availability
│   └── channel-availability.md  # set_availability_range en el puerto + Beds24 V2
└── tasks.md                     # (lo crea /speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── app/
│   ├── channels/
│   │   ├── base.py                      # + set_availability_range en el puerto
│   │   ├── beds24_v2.py                 # + set_availability_range (POST calendar numAvail) + verificación
│   │   └── beds24.py                    # + set_availability_range -> ChannelError (V1 no escribe)
│   ├── models/
│   │   └── availability.py              # + AvailabilityChangeLog (unit, date, old/new avail, blocked, origin)
│   ├── services/
│   │   ├── availability_service.py      # NUEVO — preview/apply block/open, omite reservas, audita
│   │   └── sync_service.py              # + publish_availability (resiliente, incidencia si falla)
│   ├── agent/
│   │   ├── tools.py                     # + propose_block_availability / propose_open_availability
│   │   ├── orchestrator.py              # build/apply de las nuevas propuestas
│   │   └── prompts.py                   # capacidad de disponibilidad (quitar el "no puedo")
│   └── api/routes/
│       └── pricing.py                   # POST /pricing/availability/{preview,apply}
├── migrations/versions/xxxx_availability_log.py   # NUEVO
└── tests/
    ├── test_availability_service.py     # NUEVO
    ├── test_beds24_v2_adapter.py        # + set_availability_range
    └── test_agent_orchestrator.py       # + flujo bloquear/abrir

apps/web/
├── lib/{api.ts,types.ts}                # availabilityPreview/Apply + estados
├── components/calendar/
│   ├── price-calendar.tsx               # estados visuales: bloqueada/reservada/disponible/sin datos
│   └── range-editor.tsx                 # acciones Bloquear/Abrir con preview→confirmar
└── app/(app)/calendar/page.tsx          # integra las acciones
```

**Structure Decision**: Se extiende el monorepo existente reutilizando el patrón de precios (preview→apply, AgentAction, SyncIssue). La disponibilidad vive en `CalendarDay` (ya existe); se añade un log de auditoría y un servicio dedicado. El puerto `ChannelManager` gana un método de escritura de disponibilidad (provider-agnostic).

## Complexity Tracking

> Sin violaciones de la constitución. Nada que justificar.
