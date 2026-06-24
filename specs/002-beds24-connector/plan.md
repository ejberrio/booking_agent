# Implementation Plan: Conector de Channel Manager (Beds24)

**Branch**: `002-beds24-connector` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/002-beds24-connector/spec.md`

## Summary

Conector que sincroniza el modelo local (feature 001) con Beds24 (y por ende Booking.com). Se compone de: (1) un **puerto provider-agnostic** `ChannelManager` con DTOs neutrales, (2) un **adaptador Beds24** sobre la **API V1 JSON** usando la **API Key de cuenta** (sin propKey), (3) un **servicio de sincronización** que importa (lectura → upsert local), publica precios (local → remoto con verificación) y reconcilia discrepancias sin sobrescribir, y (4) entidades de operación (conexión, corridas, incidencias). Sincronización diaria programada + manual. Tests con HTTP mockeado (sin llamar a la API real).

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: httpx (cliente async), SQLAlchemy 2.0 (modelos 001 + nuevos), Alembic, Pydantic v2 (DTOs/validación)  
**Storage**: PostgreSQL 16 (nuevas tablas de operación; reutiliza modelos de la feature 001)  
**Testing**: pytest + pytest-asyncio; **httpx MockTransport** para simular Beds24 (sin red); SQLite async para modelos  
**Target Platform**: Servidor Linux (API en `apps/api`)  
**Project Type**: Web (backend de esta feature)  
**Integration**: Beds24 **API V1 JSON** (`https://api.beds24.com/json/...`), autenticación con `apiKey` de cuenta (Allow Writes = Yes). Sin propKey (propiedad propia).  
**Performance/Constraints**: 1 propiedad, volumen pequeño; respetar rate limits con backoff; escrituras idempotentes y verificadas; secretos solo en env (nunca en repo/logs/DB).  
**Scale/Scope**: Single-tenant, 1 cuenta de Channel Manager, sync diaria + manual.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| I. Spec-Driven | Procede de spec.md (002). ✅ |
| II. Provider-agnostic | Puerto `ChannelManager` + DTOs neutrales; el adaptador Beds24 aísla todo lo propietario; el dominio solo ve `external_ref` opacos. ✅ |
| III. Human-in-the-loop / auditoría | El conector **publica** cambios ya auditados (creados por el host vía pricing_service); **no origina** cambios silenciosos. La importación de baseline hace upsert sin auditar; las divergencias se **reportan** (SyncIssue), nunca se sobrescriben en silencio. ✅ |
| IV. Tipado y pruebas | Puerto y DTOs tipados; tests del adaptador con HTTP mockeado y del servicio de sync con adaptador falso. ✅ |
| V. Simplicidad (single-tenant) | V1 + API Key de cuenta (sin propKey ni refresh de tokens); scheduling vía cron/deploy, sin orquestadores pesados. ✅ |

**Resultado**: PASS (sin violaciones).

## Project Structure

### Documentation (this feature)

```text
specs/002-beds24-connector/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── channel-manager-port.md   # interfaz provider-agnostic + DTOs
│   └── beds24-v1-mapping.md       # mapeo a endpoints Beds24 V1
├── quickstart.md
└── tasks.md            # /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/app/
├── channels/                 # NUEVO
│   ├── base.py               # Protocol ChannelManager + DTOs (RemoteProperty, RemoteRoom,
│   │                         #   RemoteRate, RemoteBooking, WriteResult, ConnectionInfo)
│   ├── beds24.py             # Beds24Adapter (httpx, V1 JSON, mapeo, backoff/rate limit)
│   └── errors.py             # ChannelError, AuthError, RateLimited, WriteUnverified
├── models/
│   └── sync.py               # NUEVO: ChannelManagerConnection, SyncRun, SyncIssue
├── services/
│   └── sync_service.py       # NUEVO: import_remote(), publish_price(), reconcile()
├── api/routes/
│   └── sync.py               # NUEVO: POST /sync/test, /sync/import, /sync/publish; GET /sync/runs
└── core/config.py            # + BEDS24_* (api_key, prop_id, room_id, base_url)

apps/api/scripts/
└── sync_daily.py             # NUEVO: entrypoint para cron (sync diaria)

apps/api/migrations/versions/  # NUEVA migración: channel_manager_connection, sync_run, sync_issue

apps/api/tests/
├── test_beds24_adapter.py    # httpx MockTransport (getProperties, getRoomDates, setRoomDates, getBookings)
└── test_sync_service.py      # import/publish/reconcile con adaptador falso (in-memory)
```

**Structure Decision**: Nuevo paquete `app/channels/` (puerto + adaptador), `app/services/sync_service.py` (orquestación), modelos de operación en `app/models/sync.py`, y endpoints en `app/api/routes/sync.py`. La programación diaria se hace por cron sobre `scripts/sync_daily.py` (sin orquestador embebido). Reutiliza los modelos y servicios de la feature 001 (`pricing_service` para escrituras auditadas).

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
