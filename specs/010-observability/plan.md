# Implementation Plan: Observabilidad en producción

**Branch**: `010-observability` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-observability/spec.md`

## Summary

Dotar a la app (ya en producción) de observabilidad proporcionada: (1) **seguimiento de errores con Sentry** en API y web (captura de excepciones no controladas, no-op sin DSN, sin secretos/PII, 0% de trazas); (2) **logging estructurado** de la API por petición en líneas legibles `key=value`; (3) un **endpoint `/status`** (protegido vía proxy) que resume versión, base de datos, Beds24 (chequeo cacheado ~5 min) y nº de incidencias de publicación abiertas, resiliente a dependencias caídas. Reutiliza `/health` (liveness para Railway) y `SyncIssue`.

## Technical Context

**Language/Version**: Python/FastAPI (apps/api, uv) + TypeScript/Next.js 15 (apps/web)
**Primary Dependencies**: nuevo `sentry-sdk[fastapi]` (api) y `@sentry/nextjs` (web); stdlib `logging`
**Storage**: sin cambios de esquema (se consulta `SyncIssue` existente)
**Testing**: pytest (api: middleware de logging, `/status`, no-op sin DSN), `npm run build` (web)
**Target Platform**: Railway (web pública + API privada) + Neon; ya en producción (CD)
**Project Type**: web (monorepo)
**Constraints**: no-op sin DSN; cero secretos/PII en logs y Sentry; best-effort (nada rompe la petición del usuario); `/status` < 2 s aun con dependencia degradada
**Scale/Scope**: single-tenant; 1 réplica (cache en proceso suficiente)

## Constitution Check

| Principio | Cumplimiento |
|-----------|--------------|
| **I. Spec-Driven** | specify→clarify→plan→tasks→implement. ✅ |
| **II. Provider-agnostic** | La observabilidad es transversal; no acopla el dominio. Sentry se activa por entorno (DSN) y es no-op sin él; el dominio no lo conoce. ✅ |
| **III. Human-in-the-loop** | No escribe ni cambia datos del negocio; solo observa. ✅ |
| **IV. Tipado y pruebas en los límites** | Tests: middleware de logging (registra una línea), `/status` (forma + degradado), no-op sin DSN, y que no se filtran secretos. Tipado mantenido. ✅ |
| **V. Simplicidad (YAGNI)** | Sentry "ligero" (sin wrapper de build pesado ni subida de source-maps en v1), cache en proceso, sin stack de métricas. ✅ |
| **Restricciones técnicas** | `send_default_pii=False`; logs sin secretos (se loguea path sin query; el adapter ya redacta); DSN por variable de entorno. ✅ |

**Resultado**: PASS, sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/010-observability/
├── plan.md
├── research.md           # Decisiones (Sentry no-op, logging, /status cacheado)
├── data-model.md         # Sin esquema nuevo; forma de /status + config
├── quickstart.md         # Cómo validar (error de prueba, logs, /status)
├── contracts/
│   ├── status-endpoint.md   # Contrato de GET /status
│   ├── error-tracking.md    # Sentry en API y web (no-op, sin PII)
│   └── request-logging.md   # Formato de log por petición
└── tasks.md                 # (lo crea /speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── pyproject.toml                 # + sentry-sdk[fastapi]
├── app/
│   ├── core/
│   │   ├── config.py              # + sentry_dsn, log_level
│   │   └── observability.py       # NUEVO — init Sentry (no-op sin DSN) + setup logging
│   ├── main.py                    # init Sentry + logging + middleware de request-logging + ruta /status
│   ├── api/routes/status.py       # NUEVO — GET /status (versión, db, beds24 cacheado, incidencias)
│   └── services/sync_service.py   # (reutiliza list_open_issues para el conteo)
└── tests/
    ├── test_request_logging.py    # NUEVO — registra method/path/status/ms; no secretos
    └── test_status.py             # NUEVO — forma + degradado + conteo de incidencias

apps/web/
├── package.json                   # + @sentry/nextjs
├── instrumentation.ts             # NUEVO — init Sentry server (no-op sin DSN)
├── instrumentation-client.ts      # NUEVO — init Sentry cliente (no-op sin DSN)
└── .env.example / contracts       # SENTRY_DSN / NEXT_PUBLIC_SENTRY_DSN

.env.example (raíz)                # + SENTRY_DSN, LOG_LEVEL
```

**Structure Decision**: cambios transversales acotados — un módulo de observabilidad + middleware + ruta `/status` en la API, e inicialización ligera de Sentry en la web (vía `instrumentation`, sin `withSentryConfig` para no acoplar el build ni subir source-maps en v1). Sin nuevas entidades ni migraciones. Reutiliza `/health` y `SyncIssue`.

## Complexity Tracking

> Sin violaciones. Integración ligera y opcional (no-op sin DSN).
