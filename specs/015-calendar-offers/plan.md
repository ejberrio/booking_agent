# Implementation Plan: Calendario con promociones y deals nativos visibles + registro manual de deals

**Branch**: `015-calendar-offers` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-calendar-offers/spec.md`

## Summary

Entidad nueva pequeña `NativeDeal` (registro informativo local, con rango de fechas abierto/medio-abierto) + CRUD en `/pricing/native-deals` + tarjeta de gestión en la sección Ofertas. El calendario marca los días con deals activos con el patrón client-side de la feature 014 (merge en el cliente; el endpoint de calendario NO se toca) y el panel lateral gana "Ofertas del día" (promos de la app desde el `GET /pricing/promotions` existente + deals). La advertencia de doble descuento se vuelve real: `preview` de promociones consulta los deals que solapan (fechas ∩ canal ∩ activo) y los nombra — y fluye gratis al agente porque usa el mismo preview.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 + React 19 (web)
**Primary Dependencies**: FastAPI + SQLAlchemy 2.0 async + Alembic (API); Tailwind v4 + shadcn/ui + react-query + sonner (web)
**Storage**: PostgreSQL (prod) / SQLite async (tests). **UNA migración**: tabla `native_deal`.
**Testing**: pytest (dobles, sin APIs reales); web `npm run build`
**Target Platform**: Railway (CD a main); verificación prod vía proxy con cookie
**Project Type**: monorepo web application (apps/api + apps/web)
**Performance Goals**: n/a (decenas de deals a lo sumo)
**Constraints**: registro 100% local (cero escrituras al canal); sin deals registrados el comportamiento es idéntico (SC-004); no romper 187 tests
**Scale/Scope**: single-tenant; ~6 archivos API + ~6 web + 1 migración

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; sin ADR (no hay decisión de arquitectura nueva: entidad local + patrón de marcado ya establecido en 014) |
| II. Provider-agnostic | ✅ NativeDeal no toca el puerto ChannelManager (es un registro local); nada propietario entra al dominio |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ los deals son escrituras LOCALES informativas (no cambian precios ni disponibilidad en ningún canal) → no requieren preview/fingerprint; las escrituras reales (promos) conservan su flujo y GANAN protección (advertencia real de doble descuento) |
| IV. Tipado y pruebas | ✅ la lógica de solape (fechas abiertas × alcance de canales) puede costar dinero si falla (doble descuento) → tests dedicados; TS en web |
| V. Simplicidad | ✅ una tabla plana, CRUD directo, merge client-side sin tocar el endpoint de calendario; sin abstracciones especulativas |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/015-calendar-offers/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── native-deals-api.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
apps/api/
├── app/models/pricing.py                  # + NativeDeal
├── migrations/versions/c9d0e1f2a3b4_native_deal.py  # NUEVA (down: b7c8d9e0f1a2)
├── app/services/native_deal_service.py    # NUEVO: CRUD + find_overlapping
├── app/services/offer_promotion_service.py # preview: warning real de doble descuento
├── app/api/routes/pricing.py              # + /pricing/native-deals (GET/POST/PATCH/DELETE)
└── tests/test_native_deals.py             # NUEVO: CRUD, solapes, warning en preview

apps/web/
├── app/(app)/offers/page.tsx              # + tarjeta "Deals nativos registrados" (CRUD)
├── app/(app)/calendar/page.tsx            # query deals + promos; marcador + OffersPanel
├── app/(app)/page.tsx                     # dashboard: marcador de deals en su calendario
├── components/calendar/price-calendar.tsx # + prop nativeDealDates (punto cian + leyenda)
├── components/calendar/offers-panel.tsx   # NUEVO: "Ofertas del día" (promos + deals)
└── lib/{types,api}.ts                     # NativeDeal + funciones
```

**Structure Decision**: monorepo existente; el único módulo nuevo con lógica es `native_deal_service` + `offers-panel`.

## Decisiones clave (detalle en research.md)

1. **Marcado y detalle client-side (patrón 014)** — el calendario NO cambia su endpoint: la web consulta `GET /pricing/native-deals` (nuevo) y `GET /pricing/promotions` (existente, ya trae nombre/descuento/alcance/fechas) y cruza por fecha en el cliente. SC-004 por construcción.
2. **`NativeDeal` plano con fechas nullable** — `date_from`/`date_to` NULL = extremo abierto ("siempre activo" = ambos NULL). Canal con el enum `ChannelKind` existente restringido a booking/airbnb en el servicio.
3. **Advertencia real en el preview existente** — `offer_promotion_service.preview` añade un warning por cada deal activo que solapa (semántica de solape con extremos abiertos + alcance: scope None = todos los canales). El agente usa el mismo preview → la protección llega al chat sin trabajo extra. La advertencia NO bloquea (warning, no error): el host puede querer combinar a propósito.
4. **CRUD sin fingerprint** — los deals son registro local informativo (no tocan el canal); el patrón preview→confirm del Principio III aplica a escrituras al canal, no a anotaciones. DELETE real permitido (es una nota, no auditoría).
5. **Semilla vía API en prod, con confirmación del host** — los 3 deals reales se registran tras el deploy usando el CRUD (no en la migración: son datos del host, no del esquema).
6. **Panel "Ofertas del día"** — tarjeta nueva en la columna lateral (convive con SuggestionPanel/RangeEditor); dashboard recibe también el marcador (misma prop del componente compartido).

## Fase 0 → research.md · Fase 1 → data-model.md, contracts/, quickstart.md

Sin NEEDS CLARIFICATION: incógnitas resueltas leyendo el código (la "advertencia genérica" actual resultó estar solo en la guía de la web y el prompt — el warning real es NUEVO en el preview; `GET /pricing/promotions` ya expone todo lo que el panel necesita).
