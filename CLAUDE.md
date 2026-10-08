<!-- SPECKIT START -->
Feature activa: **022-discount-as-promotion** (bajar con promoción; issue #128).
Plan: `specs/022-discount-as-promotion/{plan,research,data-model,quickstart}.md` + `contracts/promo-batch-api.md`.
Decisiones del host (2026-10-09): TODA bajada sugerida = promoción temporal (base nunca baja por sugerencia;
subidas siguen cambiando el base); piso = precio mínimo por noche en COP (`PricingRule.min_price`, GET/PUT
/pricing/min-price); publicar en Booking.com + Airbnb. Diseño: lote 019 con `mode` base|promotion por noche;
tramos contiguos de igual base y precio promo → `offer_promotion_service.apply(price=…, origin=suggestion)`
en SAVEPOINT (issue/excepción → rollback + SyncIssue); `conditions.source="suggestion"` + suggestion_ids;
`app/domain/promo_floor.py` PURO: precio_promo ≥ max(min, max_c min/(1−a_c)) con a_c = deals `stacking=always`
del canal; <1 % u omitida por mínimo. Migración `c6d7e8f9a0b1`: native_deal.stacking (mobile→always),
price_suggestion.applied_promotion_id. Ofertas: source, finished (end<hoy), no_free_nights. es/en/pt.
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
