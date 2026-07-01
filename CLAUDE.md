<!-- SPECKIT START -->
Feature activa: **011-api-promotions** (gestión de promociones de precio vía API del Channel Manager).
Plan e artefactos: `specs/011-api-promotions/plan.md`, `research.md`, `data-model.md`,
`contracts/{promotions-api,channel-fixedprices}.md`, `quickstart.md`.
Hallazgo (2026-07-01): Beds24 V2 SÍ escribe promociones vía `POST /inventory/fixedPrices` (array;
crear=sin id; máx 100/room; NO hay DELETE), ligadas a una oferta por `offerId` (el slot es solo
lectura). Decisiones: nueva entidad `Promotion` (external_id, offer_id, fechas, price, discount_pct,
min_nights, status); oferta DESIGNADA por config `beds24_promo_offer_id`; descuento en % o precio pero
se envía precio absoluto (se guarda % y base); retirada = neutralizar (roomPriceEnable=false) + ocultar;
patrón preview→apply humano-en-el-bucle (AgentAction/SyncIssue); puerto ChannelManager +set/get/disable
fixed price. Corrige la conclusión de la Feature 009 (que asumió que no se podía por API). ADR 0003.
App YA EN PRODUCCIÓN (Railway web+api + Neon, CD). Features 001-010 en `main`.
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
