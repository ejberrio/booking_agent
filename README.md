# Booking AI Agent

Plataforma para simplificar la gestión de precios y promociones de [Booking.com](https://www.booking.com/) mediante un **agente de IA**: chatea para consultar y ajustar precios por día/rango, recibe sugerencias basadas en eventos de Medellín y precios de mercado, y mantén el control con confirmación y auditoría de cada cambio.

> Estado: scaffolding inicial (Fase 1). La planificación vive en el [GitHub Project #1](https://github.com/users/ejberrio/projects/1).

## Arquitectura

Monorepo con dos aplicaciones:

| App | Stack | Puerto |
|-----|-------|--------|
| `apps/web` | Next.js + TypeScript + Tailwind + shadcn/ui | 3000 |
| `apps/api` | FastAPI + Python + SQLAlchemy + LiteLLM | 8000 |
| `db` | PostgreSQL (docker-compose) | 5432 |

- **Integración con Booking.com** vía **Channel Manager** (Beds24/Hostaway/Smoobu/Lobby) detrás de un adaptador — Booking no ofrece API directa a hosts individuales. Ver [ADR-0001](docs/adr/0001-arquitectura.md).
- **LLM multi-proveedor** (LiteLLM), configurable por UI.
- **Single-tenant** (herramienta personal) en esta etapa.

Decisiones de arquitectura: [`docs/adr/`](docs/adr/). Principios del proyecto: [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Arranque rápido

```bash
cp .env.example .env          # completa las claves (opcional para modo demo)
make db-up                    # Postgres en Docker
make setup                    # instala dependencias (api + web)
make api                      # API en http://localhost:8000  (otra terminal)
make web                      # Web en http://localhost:3000
```

Sin claves de LLM, el chat responde en "modo demo". Configura `ANTHROPIC_API_KEY` en `.env` para activar el agente.

## Despliegue (producción)

Web pública (Next.js) + API privada (FastAPI) en **Railway**, Postgres en **Neon** (gratis). La web hace de proxy server-side hacia la API por la red interna (la API no se expone a internet). Guía paso a paso: [`docs/deploy.md`](docs/deploy.md). Decisión de arquitectura: [ADR 0002](docs/adr/0002-deploy-railway-neon.md).

## Spec-Driven Development (GitHub Spec Kit)

Este repo usa [Spec Kit](https://github.com/github/spec-kit). Flujo por feature, con skills de Claude Code:

1. `/speckit-constitution` — principios (ya redactados).
2. `/speckit-specify` — especifica la feature.
3. `/speckit-plan` — plan técnico.
4. `/speckit-tasks` — tareas accionables.
5. `/speckit-implement` — implementación.

## Estructura

```
apps/web/         # Next.js (frontend)
apps/api/         # FastAPI (backend, agente, pricing)
docs/adr/         # decisiones de arquitectura
.specify/         # Spec Kit (constitution, plantillas, scripts)
docker-compose.yml
Makefile
```
