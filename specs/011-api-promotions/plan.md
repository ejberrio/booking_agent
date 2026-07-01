# Implementation Plan: Gestión de promociones de precio vía API

**Branch**: `011-api-promotions` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-api-promotions/spec.md`

## Summary

Permitir al host **crear, ver, editar y retirar promociones de precio** (un precio con descuento sobre un rango de fechas, con estancia mínima opcional) desde la app —por chat y por el calendario— con el patrón humano-en-el-bucle (proponer→confirmar→aplicar→publicar→auditar). Aprovecha el hallazgo verificado (2026-07-01): la API **Beds24 V2 escribe promociones** vía `POST /inventory/fixedPrices` (array de `fixedPrice`; crear = sin `id`; máx. 100/room), ligadas a una **oferta designada** por configuración (`offerId`). Reutiliza el `Beds24V2Adapter`, el patrón de propuesta/confirmación de precios (`AgentAction`, `RangeSelection`, fingerprint) y el registro de incidencias (`SyncIssue`). Como la API **no expone DELETE**, la retirada se implementa **neutralizando** el fixed price (deshabilitar su precio / precio ≥ base) y marcándolo inactivo. Fuera de alcance v1: crear el contenedor de oferta por API (solo lectura) y la aparición como promo **nativa** de Booking.com (Genius/Deals), que depende del mapeo de canal.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI (apps/api, uv) + TypeScript / Next.js 15 (apps/web)
**Primary Dependencies**: sin nuevas dependencias; `Beds24V2Adapter` (httpx) existente, SQLAlchemy 2.0 async + Alembic
**Storage**: PostgreSQL (Neon en prod) — nueva tabla `promotion` (+ posible `promotion_change_log` o reutilizar auditoría existente)
**Testing**: pytest (adapter con httpx.MockTransport; servicio; agente; validaciones), `npm run build`/lint (web)
**Target Platform**: Railway (web pública + API privada) + Neon; ya en producción (CD)
**Project Type**: web (monorepo apps/api + apps/web)
**Performance Goals**: interacción humana; una promo se crea/verifica en < 2 s de proceso (SC-001 mide < 2 min extremo a extremo con el host)
**Constraints**: human-in-the-loop NON-NEGOTIABLE; nada rompe la petición si el canal falla (best-effort + `SyncIssue`); sin secretos en logs; precio absoluto al canal (no hay % nativo); máx. 100 fixed prices/room
**Scale/Scope**: single-tenant, 1 propiedad/habitación principal (propertyId 337229, roomId 697411); 1 oferta designada

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| **I. Spec-Driven** | specify→clarify→plan→tasks→implement; ADR nuevo (`0003-api-promotions.md`) que documenta el hallazgo y corrige la conclusión de 009. ✅ |
| **II. Provider-agnostic** | La lógica de promociones vive en un `promotion_service` de dominio; el detalle de `fixedPrices`/`offerId` queda dentro del adaptador (se añade `set_fixed_price`/`get_fixed_prices`/`disable_fixed_price` al puerto `ChannelManager`). El dominio habla de "promoción", no de Beds24. ✅ |
| **III. Human-in-the-loop (NON-NEGOTIABLE)** | Crear/editar/retirar SIEMPRE proponen y solo aplican tras confirmación; auditoría en `AgentAction`; retirada = operación inversa (neutraliza), reversible. ✅ |
| **IV. Tipado y pruebas en los límites** | Tests del adapter (crear/leer/neutralizar fixed price con MockTransport), del servicio (cálculo de descuento %, validaciones precio≤0/≥base/fechas, solape, estancia mínima), del agente (tools proponer/aplicar) y de esquemas. Pricing/adapter no se mergea sin pruebas. ✅ |
| **V. Simplicidad (YAGNI)** | Una oferta designada (no selector múltiple), solo precio de habitación (no per-persona en v1), sin descuentos porcentuales automáticos del canal, sin DELETE inventado. Reutiliza patrones existentes. ✅ |
| **Restricciones técnicas** | Stack respetado; `offerId` designado por config/env (no secreto); token V2 ya cifrado en env; sin credenciales en logs (el adapter ya redacta). ✅ |

**Resultado**: PASS, sin violaciones. (Complexity Tracking vacío.)

## Project Structure

### Documentation (this feature)

```text
specs/011-api-promotions/
├── plan.md              # Este archivo
├── research.md          # Fase 0 — decisiones (endpoint fixedPrices, retirada sin DELETE, oferta designada, % almacenado)
├── data-model.md        # Fase 1 — entidad Promotion + estados + mapeo a fixedPrice
├── quickstart.md        # Fase 1 — cómo validar (crear/ver/editar/retirar; verificación de escritura acotada)
├── contracts/
│   ├── promotions-api.md      # Endpoints internos /pricing/promotions/*
│   └── channel-fixedprices.md # Contrato con el canal (POST/GET fixedPrices, neutralizar)
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── app/
│   ├── channels/
│   │   ├── base.py                  # + puerto: set_fixed_price / get_fixed_prices / disable_fixed_price (tipos RemoteFixedPrice)
│   │   └── beds24_v2.py             # impl V2: POST/GET /inventory/fixedPrices; neutralizar (roomPriceEnable=false / precio≥base)
│   ├── models/
│   │   └── promotion.py             # NUEVO — modelo Promotion (external_id, offer_id, fechas, precio, pct, min_nights, estado)
│   ├── schemas/
│   │   └── promotion.py             # NUEVO — PromotionCreate/Preview/View/ApplyResult + fingerprint
│   ├── services/
│   │   ├── promotion_service.py     # NUEVO — preview/apply/list/edit/retire; cálculo de descuento; validaciones; solape
│   │   └── sync_service.py          # + publish_promotion / retire_promotion (resiliente, SyncIssue)
│   ├── agent/
│   │   ├── tools.py                 # + propose_create_promotion (real) / propose_edit_promotion / propose_retire_promotion / get_promotions
│   │   ├── prompts.py               # reglas: promo = precio+fechas(+minNights) sobre oferta designada; distinguir de deal nativo
│   │   └── orchestrator.py          # feedback de validación (ValueError) para las nuevas tools
│   ├── api/routes/
│   │   └── pricing.py               # + /pricing/promotions (GET list, POST preview, POST apply, POST retire)
│   └── core/config.py               # + beds24_promo_offer_id (oferta designada)
└── tests/
    ├── test_beds24_v2_promotions.py # crear/leer/neutralizar fixed price (MockTransport)
    ├── test_promotion_service.py    # descuento %, validaciones, solape, estancia mínima, retirada
    └── test_agent_promotions.py     # tools proponer/aplicar/retirar + guardas

apps/web/
├── app/(app)/offers/page.tsx        # evolucionar 009: de solo deep-links a gestión real (lista + crear/editar/retirar)
├── components/calendar/             # acción "Crear promoción" desde el rango del calendario (reutiliza range-editor)
└── lib/{api,types}.ts               # tipos + llamadas a /pricing/promotions
```

**Structure Decision**: monorepo web existente. El dominio nuevo (`promotion_service` + modelo `Promotion`) y la extensión del puerto `ChannelManager` mantienen a Beds24 encapsulado (Principio II). La UI evoluciona la sección "Ofertas" de la Feature 009 (que era solo deep-links) a gestión real, más una acción desde el calendario. Migración Alembic nueva para `promotion`.

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
