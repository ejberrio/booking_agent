<!-- SPECKIT START -->
Feature activa: **020-beds24-webhooks** (reservas en tiempo real; issue #117).
Plan: `specs/020-beds24-webhooks/{plan,research,data-model,quickstart}.md` + `contracts/webhooks-api.md`.
Beds24 Booking Webhook V2 (Settings → Properties → Access): POST JSON {timeStamp, booking{id, propertyId,
arrival, departure, …PII y tokens de pago}}, reintenta si respuesta ≥ 400, campo Custom Header.
Diseño: entrada pública web `POST /api/hooks/beds24` (sin sesión, ≤256 KB, sin logs) → API privada
`POST /hooks/beds24`; clave `X-StayLever-Key` vs secreto `beds24_webhook_key` (hmac.compare_digest;
generada por la app y mostrada UNA vez en `POST /hooks/beds24/key`); el cuerpo es solo PISTA
(id/propertyId/arrival/departure, nunca se persiste): se re-sincroniza el rango (± estancia previa) con
`import_remote` → Beds24 es la verdad, idempotente y sin datos inyectables. 200 accepted/ignored/failed
(failed no se reintenta: el cron corrige), 401 rechazado, 503 sin clave. Bitácora `webhook_event` sin
PII (purga > 30 días); estado en Ajustes (unconfigured/never/active/idle >7 días). Migración
`a4b5c6d7e8f9`. Sin escrituras al canal; bloqueos manuales intactos.
<!-- SPECKIT END -->

# Booking AI Agent

Plataforma single-tenant para gestionar precios/promociones de Booking.com con un agente de IA.

## Arquitectura
- Monorepo: `apps/web` (Next.js + TS + Tailwind + shadcn) y `apps/api` (FastAPI + SQLAlchemy + LiteLLM). Postgres vía `docker-compose`.
- Booking.com se integra **vía Channel Manager** (adaptador provider-agnostic), no API directa. Ver `docs/adr/0001-arquitectura.md`.
- LLM multi-proveedor (LiteLLM), configurable. Principios en `.specify/memory/constitution.md`.

## Comandos
- `make setup` — instala deps (api: `uv sync`, web: `npm install`)
- `make api` / `make web` — corre API (:8000) / web (:3000)
- `make test` — `uv run pytest` en la API
- `make lint` — ruff + next lint

## Convenciones
- Spec-Driven: features con `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
- Escrituras de precio siempre con confirmación + audit log (principio III, no negociable).
- Integraciones (Channel Manager, LLM, búsqueda) detrás de interfaces; nada propietario en el dominio.
- Planificación en GitHub Project #1 (milestones = Fases 1–7).
