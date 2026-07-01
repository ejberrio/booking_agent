---
description: "Task list — Observabilidad en producción"
---

# Tasks: Observabilidad en producción

**Input**: Design documents from `/specs/010-observability/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Constitución IV — tests para el middleware de logging, `/status` (forma + degradado) y el no-op de Sentry sin DSN.

**Organization**: por historia — US1 (seguimiento de errores, P1), US2 (logging estructurado, P2), US3 (endpoint /status, P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivos distintos, sin dependencias. Monorepo: `apps/api/`, `apps/web/`.

---

## Phase 1: Setup

- [X] T001 [P] Añadir variables de config `sentry_dsn: str | None = None` y `log_level: str = "INFO"` en `apps/api/app/core/config.py`; y `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, `LOG_LEVEL` al `.env.example` (raíz)
- [X] T002 [P] Añadir `sentry-sdk[fastapi]` a `apps/api/pyproject.toml` (dependencies) y `uv sync`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Módulo de observabilidad compartido por errores (US1) y logging (US2).

- [X] T003 Crear `apps/api/app/core/observability.py` con `init_sentry(dsn, environment, release)` (NO-OP si `dsn` es None; `traces_sample_rate=0.0`, `send_default_pii=False`) y `setup_logging(level)` (formato a stdout)

**Checkpoint**: helpers de Sentry (no-op) y de logging disponibles.

---

## Phase 3: User Story 1 - Seguimiento de errores (Priority: P1) 🎯 MVP

**Goal**: Excepciones no controladas de API y web se reportan a Sentry con contexto, sin secretos; no-op sin DSN.

**Independent Test**: forzar un error de prueba en API y web y verlo en Sentry (con DSN); sin DSN, la app arranca y opera normal.

- [X] T004 [US1] En `apps/api/app/main.py`, llamar `init_sentry(settings.sentry_dsn, settings.environment, app.version)` al inicio (antes de crear/usar la app)
- [X] T005 [US1] Web: añadir `@sentry/nextjs` a `apps/web/package.json`; crear `apps/web/instrumentation.ts` (init server, no-op sin DSN) y `apps/web/instrumentation-client.ts` (init cliente); `tracesSampleRate: 0`. Sin `withSentryConfig`
- [X] T006 [US1] Test en `apps/api/tests/test_observability.py`: `init_sentry(None, ...)` es no-op (no lanza; Sentry no queda "inicializado" con DSN)

**Checkpoint**: errores capturados en prod; app intacta sin DSN.

---

## Phase 4: User Story 2 - Logging estructurado de la API (Priority: P2)

**Goal**: Cada petición deja una línea `method=… path=… status=… ms=…` (path sin query, sin secretos); errores con traza; nivel configurable.

**Independent Test**: hacer peticiones (alguna que falle) y ver una línea por petición con método/ruta/status/duración; los errores con traza; sin secretos.

- [X] T007 [US2] En `apps/api/app/main.py`: llamar `setup_logging(settings.log_level)` y añadir un middleware HTTP que mida duración y loguee `method=… path=<sin query> status=… ms=…`; en excepción, log con `exc_info`
- [X] T008 [US2] Test en `apps/api/tests/test_request_logging.py`: una petición produce exactamente una línea con method/path/status/ms; verificar que no aparece query/secretos

**Checkpoint**: logs por petición legibles y sin secretos.

---

## Phase 5: User Story 3 - Endpoint /status (Priority: P2)

**Goal**: `GET /status` (protegido vía proxy) devuelve version, db, beds24 (cacheado ~5 min) y open_issues; resiliente a dependencias caídas.

**Independent Test**: consultar `/status` y obtener los 4 campos coherentes; con DB caída → `db=down`; con incidencias abiertas → `open_issues` coincide; responde < 2 s aun degradado.

- [X] T009 [US3] Crear `apps/api/app/api/routes/status.py`: `GET /status` → `{version, environment, db, beds24, open_issues}`; cada check en try/except con timeout; beds24 con cache en proceso (~5 min) usando el adapter (`sync_service.test_connection`); `open_issues` vía `sync_service.list_open_issues`. Registrar el router en `apps/api/app/api/router.py`
- [X] T010 [US3] Test en `apps/api/tests/test_status.py`: forma OK; DB caída → `db=down` sin colgarse; `open_issues` refleja las incidencias creadas

**Checkpoint**: foto de estado del sistema, resiliente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T011 [P] Documentar en `docs/operations.md` las variables (`SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, `LOG_LEVEL`), el endpoint `/status` y cómo crear el proyecto Sentry (acción del host)
- [X] T012 Ejecutar `uv run ruff check . && uv run pytest` (api) y `npm run build` (web) — todo verde
- [X] T013 Validar `quickstart.md`: en prod, `/status` vía el proxy responde con los campos; los logs muestran líneas por petición; sin DSN todo sigue igual

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: T001, T002.
- **Foundational (Phase 2)**: T003 (observability.py) — depende de T001; **bloquea** US1 (T004) y US2 (T007).
- **US1 (Phase 3)**: T004 (usa T003) ‖ T005 (web, independiente).
- **US2 (Phase 4)**: T007 (usa T003).
- **US3 (Phase 5)**: independiente de US1/US2 (solo reutiliza sync_service y config).
- **Polish (Phase 6)**: al final.

## Parallel Opportunities

- Setup: T001 ‖ T002.
- Tras T003: **US1 (errores)**, **US2 (logging)** y **US3 (/status)** pueden avanzar en paralelo (web de US1 es del todo independiente).

## Implementation Strategy

### MVP
1. Setup + Foundational (T003).
2. US1 (Sentry) → el mayor valor: enterarse de los fallos.
3. US2 (logging) + US3 (/status) → diagnóstico y foto de estado.

### Notas
- Sin entidades ni migraciones (reutiliza SyncIssue).
- No-op sin DSN (FR-002): la app nunca debe fallar por la observabilidad.
- Cero secretos/PII en logs ni Sentry (FR-003).
