# Implementation Plan: Núcleo multi-canal (Booking.com + Airbnb)

**Branch**: `012-multichannel-core` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-multichannel-core/spec.md`

## Summary

La app etiqueta hoy TODA reserva importada como `ChannelKind.booking` (hardcoded) y el agente se presenta como "solo el canal Booking", pese a que Beds24 ya sincroniza Booking **y** Airbnb (issue #86). El plan: (1) el puerto `ChannelManager` transporta el canal de origen de cada reserva (`RemoteBooking.channel`, concepto neutro), los adaptadores Beds24 lo mapean desde `channel`/`referer`; (2) `sync_service` normaliza el origen a `ChannelKind` (booking/airbnb/desconocido→direct), lo usa al crear reservas y **corrige el canal de reservas existentes al re-importar** (fix de históricos sin migración de esquema); (3) los canales activos se registran desde configuración (`CHANNELS_ACTIVE`, default `booking,airbnb`); (4) el agente recibe los canales activos en el prompt y `get_bookings` gana filtro/salida por canal; (5) `/status` y el dashboard web muestran canales + reservas por canal; (6) textos multi-canal. **Cero cambios de esquema de BD** (los modelos ya son channel-aware) y cero cambios de escritura (Principio III intacto).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript/React 19 (web)
**Primary Dependencies**: FastAPI + SQLAlchemy 2.0 async + Pydantic (api); Next.js 15 App Router + Tailwind v4 + shadcn/ui + react-query (web)
**Storage**: PostgreSQL (Neon en prod); SQLite async en tests. Sin migraciones nuevas (esquema ya channel-aware: `Booking.channel_kind`, `Channel.kind` enum booking/airbnb/direct)
**Testing**: pytest + pytest-asyncio con dobles del Channel Manager (sin APIs reales); `npm run build` para web
**Target Platform**: Railway (web pública + api privada), CD al push a main
**Project Type**: web application (monorepo apps/api + apps/web)
**Performance Goals**: /status responde < 5 s (SC-004); import de reservas sin cambio de complejidad (una pasada)
**Constraints**: single-tenant; conector `beds24_v2` sin cambios de endpoints (solo mapeo de un campo ya devuelto); no romper las 109 pruebas existentes
**Scale/Scope**: 1 propiedad, 2 canales OTA + directo; ~10 archivos tocados, 0 migraciones

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec.md aprobada; este plan la implementa; sin ADR nuevo (no hay decisión de arquitectura mayor; el cambio de puerto se documenta en contracts/) |
| II. Provider-agnostic | ✅ El puerto gana `RemoteBooking.channel: str \| None` como **concepto neutro** (token normalizado del origen); el mapeo propietario (`channel`/`referer` de Beds24) vive solo en los adaptadores. Ningún detalle Beds24 llega al dominio |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ Feature de lectura/etiquetado: no añade escrituras al canal. La corrección de históricos ocurre dentro del import existente (idempotente); las escrituras existentes no se tocan |
| IV. Tipado y pruebas en los límites | ✅ DTO tipado en el puerto; tests nuevos para: normalización de origen, corrección en re-import sin duplicados, filtro por canal del agente, /status por canal. Adapters no se mergean sin pruebas |
| V. Simplicidad (YAGNI) | ✅ Sin tablas nuevas, sin migraciones, sin detección automática de conexión de canal (config explícita `CHANNELS_ACTIVE`); se reutilizan `ChannelKind`, `Channel` y el import existente |

**Post-diseño (re-check)**: sin violaciones; no aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-multichannel-core/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── channel-manager-port.md   # Cambio del puerto (RemoteBooking.channel)
│   ├── status-api.md             # GET /status extendido
│   └── agent-tools.md            # get_bookings con canal
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── app/
│   ├── channels/
│   │   ├── base.py            # RemoteBooking += channel (token neutro, None=desconocido)
│   │   ├── beds24_v2.py       # get_bookings: mapea b["channel"] (fallback referer) → token
│   │   └── beds24.py          # V1 (solo lecturas): mapea referer → token, best-effort
│   ├── core/config.py         # += channels_active: str = "booking,airbnb" (CSV)
│   ├── services/sync_service.py  # _map_channel(); usa canal real al crear; corrige en re-import;
│   │                             # _upsert_property registra canales desde config (no hardcode)
│   ├── agent/
│   │   ├── prompts.py         # system_prompt(active_channels=...) multi-canal
│   │   ├── orchestrator.py    # inyecta canales activos al prompt
│   │   └── tools.py           # get_bookings: += channel (filtro opcional + en la salida)
│   ├── api/routes/status.py   # += channels: [{kind, is_active, bookings}]
│   └── main.py                # description multi-canal
└── tests/
    ├── test_beds24_v2_channels.py # NUEVO: mapeo channel/referer en el adaptador V2
    ├── test_sync_channels.py      # NUEVO: normalización, creación, corrección re-import
    ├── test_agent_bookings.py     # NUEVO: tool get_bookings con filtro/salida por canal
    ├── test_agent_prompts.py      # NUEVO: prompt multi-canal + retro-compatibilidad
    ├── test_status.py             # ext: bloque channels
    └── test_agent_orchestrator.py # ajustar aserciones del prompt

apps/web/
├── app/(app)/page.tsx        # Dashboard: tarjeta "Canales" (conectados + reservas por canal)
├── app/layout.tsx            # description multi-canal
└── lib/{api.ts,types.ts}     # getStatus() + tipos del bloque channels
```

**Structure Decision**: monorepo existente (apps/api + apps/web); esta feature toca el puerto, un servicio, el agente, un endpoint y una tarjeta del dashboard. Sin módulos nuevos.

## Diseño (decisiones clave)

1. **Puerto**: `RemoteBooking.channel: str | None = None` — token neutro en minúsculas (`"booking"`, `"airbnb"`, otros posibles); `None` = el proveedor no reporta origen. Campo con default ⇒ compatible con dobles/tests existentes.
2. **Adaptadores**: `beds24_v2.get_bookings` toma `b.get("channel")` y si falta infiere de `referer` ("Booking.com"→`booking`, "Airbnb"→`airbnb`); normaliza a minúsculas. V1 igual con `referer` (best-effort; V1 es legacy de solo lectura).
3. **Normalización en dominio**: `sync_service._map_channel(token) -> ChannelKind` — `booking*`→booking, `airbnb*`→airbnb, resto/None→**direct** (FR-002: nunca aborta el lote).
4. **Corrección de históricos SIN migración**: en el import, si la reserva ya existe y su `channel_kind` difiere del reportado, se actualiza (cuenta como `updated`). Re-importar = corregir (FR-004); la des-duplicación existente por `external_ref` garantiza 0 duplicados.
5. **Canales activos por configuración**: `CHANNELS_ACTIVE=booking,airbnb` (settings, default). `_upsert_property` upserta un `Channel` por cada kind configurado (activo) y desactiva los registrados no configurados. Desconectar Airbnb = quitarlo de la config (edge case del spec cubierto de forma explícita y simple; sin detección automática — YAGNI, ver research R3).
6. **Agente**: `system_prompt(today, active_channels)`; el texto declara los canales activos y que precios/disponibilidad/promos publican a todos los canales conectados (FR-006). `get_bookings` acepta `channel` opcional (booking|airbnb|direct) y devuelve `channel` por reserva (FR-005).
7. **/status**: bloque `channels` desde la BD (consulta barata con try/except aislado, patrón del endpoint): `[{"kind":"booking","is_active":true,"bookings":12}, ...]` (FR-007).
8. **Web**: tarjeta "Canales" en el dashboard usando `GET /api/proxy/status` (ya autenticado por cookie); textos/metadata multi-canal (FR-008/FR-009).

## Complexity Tracking

Sin violaciones a la constitución — no aplica.
