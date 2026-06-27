# Implementation Plan: Despliegue en producción (Railway + Neon)

**Branch**: `007-production-deploy` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-production-deploy/spec.md`

## Summary

Llevar Booking_AI_Agent a producción con la web (Next.js) como **único servicio público** en Railway, la API (FastAPI) en la **red privada** de Railway (no expuesta a internet), y Postgres gestionado en **Neon** (tier gratis). La web hace de **proxy server-side** hacia la API por la red interna, de modo que el navegador nunca habla con la API directamente: esto cierra el hueco de seguridad (hoy la API no tiene auth) reutilizando el gate de contraseña ya existente y elimina CORS. Migraciones automáticas al desplegar, escaneo de mercado diario por cron, despliegue continuo al hacer push a `main`, y `/health` que además verifica la base de datos.

## Technical Context

**Language/Version**: Python (apps/api, gestionado con `uv`) + TypeScript/Node (apps/web, Next.js 15 / React 19)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 async, Alembic, asyncpg, httpx (api); Next.js App Router, @tanstack/react-query (web)
**Storage**: PostgreSQL gestionado en **Neon** (tier gratis, conexión SSL obligatoria)
**Testing**: pytest (api, httpx.MockTransport para externos), `npm run build` + lint (web)
**Target Platform**: **Railway** (contenedores Linux) — web pública, API privada, job cron; **Neon** (DB)
**Project Type**: web (monorepo: `apps/web` frontend + `apps/api` backend)
**Performance Goals**: uso personal single-tenant, baja concurrencia; arranque tolerante a Neon autosuspend (reconexión transparente)
**Constraints**: presupuesto ~US$5/mes (Railway Hobby por uso) + Neon $0; servicios pequeños; imágenes livianas; sin orquestador nuevo; secretos solo por variables de entorno
**Scale/Scope**: 1 host, 1 propiedad; ~2 servicios de cómputo + 1 cron + 1 DB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| **I. Spec-Driven** | Esta feature sigue specify→clarify→plan→tasks→implement. Las decisiones de arquitectura del deploy se registran en un ADR (`docs/adr/0002-deploy-railway-neon.md`). ✅ |
| **II. Integraciones provider-agnostic** | El deploy no toca los adaptadores; Beds24/LLM/búsqueda siguen detrás de sus puertos. El proveedor de hosting (Railway) y de DB (Neon) se configuran por entorno, sin acoplar el dominio. ✅ |
| **III. Human-in-the-loop (NO NEGOCIABLE)** | El escaneo diario por cron **solo genera sugerencias** (propuestas), nunca escribe precios. Las escrituras siguen exigiendo confirmación explícita. El proxy no introduce caminos que salten la confirmación. ✅ |
| **IV. Tipado y pruebas en los límites** | Se añaden pruebas para la normalización de la URL/SSL de la DB y para el `/health` con verificación de DB (puntos que pueden tumbar producción). Tipado se mantiene (Pydantic/TS). ✅ |
| **V. Simplicidad (single-tenant, YAGNI)** | 2 servicios + 1 cron + DB gestionada; CD nativo de Railway (sin pipeline propio); sin colas/microservicios. El proxy es un route handler mínimo. ✅ |
| **Restricciones técnicas** | Secretos solo por variables de entorno de Railway, nunca en repo/logs; DB cifrada (SSL). ✅ |

**Resultado**: PASS, sin violaciones (Complexity Tracking vacío).

## Project Structure

### Documentation (this feature)

```text
specs/007-production-deploy/
├── plan.md              # Este archivo
├── research.md          # Decisiones técnicas (Phase 0)
├── data-model.md        # Sin cambios de esquema; catálogo de config
├── quickstart.md        # Runbook del operador (Neon + Railway)
├── contracts/
│   ├── environment.md   # Catálogo de variables de entorno por servicio
│   ├── health.md        # Contrato de GET /health (liveness + DB)
│   └── web-api-proxy.md # Contrato del proxy web→API (red privada)
└── tasks.md             # (lo crea /speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── Dockerfile                 # NUEVO — imagen uv, arranca migraciones + uvicorn
├── .dockerignore              # NUEVO
├── scripts/
│   ├── start.sh               # NUEVO — alembic upgrade head && uvicorn :$PORT
│   └── scan_daily.py          # (existe) — lo invoca el cron
├── app/
│   ├── core/config.py         # + normalización SSL de DATABASE_URL para Neon
│   ├── db/session.py          # usa connect_args/SSL normalizado
│   └── api/routes/health.py   # /health ahora verifica la DB (SELECT 1)
├── migrations/env.py          # usa la misma normalización SSL
└── tests/
    ├── test_db_url_ssl.py     # NUEVO — normalización de URL/SSL
    └── test_health.py         # NUEVO — health degradado si la DB no responde

apps/web/
├── Dockerfile                 # NUEVO — build Next standalone, server.js :$PORT
├── .dockerignore              # NUEVO
├── next.config.ts             # + output: 'standalone'
├── app/api/proxy/[...path]/route.ts  # NUEVO — proxy server-side a la API privada
└── lib/api.ts                 # base relativa ("/api/proxy") en vez de NEXT_PUBLIC_API_URL

docs/
├── deploy.md                  # NUEVO — guía del operador (= quickstart)
└── adr/0002-deploy-railway-neon.md  # NUEVO — ADR de la decisión

railway.json (o config por servicio en el dashboard)  # NUEVO/según enfoque
```

**Structure Decision**: Se mantiene el monorepo existente (`apps/web` + `apps/api`). El deploy añade artefactos de contenedor y un proxy en la web; **no** se reestructura el código de dominio. La API pierde su exposición pública (pasa a red privada) y la web gana un route handler de proxy. El cron reutiliza la imagen de la API.

## Complexity Tracking

> Sin violaciones de la constitución. Nada que justificar.
