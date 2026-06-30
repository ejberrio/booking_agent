# Implementation Plan: Ofertas de Booking.com (v1 ligera: guía + claridad)

**Branch**: `009-booking-offers` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-booking-offers/spec.md`

## Summary

**Hallazgo del plan (verificado en vivo, ver [research.md](research.md))**: la API de Beds24 V2 **no gestiona los deals de Booking.com** (ni crear, ni listar; se gestionan en el dashboard de Beds24 / extranet de Booking). Por tanto, v1 NO sincroniza ofertas por API. En su lugar entrega lo realmente valioso y construible:

1. **Claridad del agente**: ante "una promoción que se vea en Booking", el agente explica que esos deals se gestionan en Beds24/Booking (no por la app) y da el enlace — sin crear por error una promoción de precio interna. A la inversa, "bajar el precio" → promoción interna.
2. **Sección "Ofertas" en la web** (menú lateral): explica la distinción (Ofertas de Booking visibles vs Promociones de precio internas) y ofrece **deep-links** al dashboard de Beds24 (Channel Manager → Booking.com → Promotions) y al extranet de Booking, con un mini-instructivo.

Sin creación/lectura por API ni indicador de ofertas en el calendario (no hay datos sincronizados).

## Technical Context

**Language/Version**: TypeScript/Next.js 15 (apps/web) + Python/FastAPI (apps/api, solo prompt del agente)
**Primary Dependencies**: Next.js App Router (web); el backend solo ajusta el prompt del agente
**Storage**: ninguno nuevo (no se persisten ofertas; v1 es guía/enlaces)
**Testing**: `npm run build` (web); pytest (api) por el ajuste del agente
**Target Platform**: Railway (web+api) + Neon; ya en producción (CD)
**Project Type**: web (monorepo)
**Constraints**: la API del Channel Manager no expone deals de Booking → v1 es informativa/deep-link
**Scale/Scope**: 1 host; una página nueva + un ajuste de prompt

## Constitution Check

| Principio | Cumplimiento |
|-----------|--------------|
| **I. Spec-Driven** | specify→clarify→plan; el plan registró un hallazgo que re-alcanzó la feature (documentado en research.md y Clarifications). ✅ |
| **II. Provider-agnostic** | No se acopla nada nuevo al proveedor; se documenta que el deal es externo. Los enlaces son configurables. ✅ |
| **III. Human-in-the-loop** | v1 no escribe nada (solo informa/enlaza); ninguna acción automática sobre Booking. ✅ |
| **IV. Tipado y pruebas en los límites** | Cambio acotado; el ajuste del agente se cubre con una prueba de comportamiento (no propone precio; deriva al dashboard). Web tipada. ✅ |
| **V. Simplicidad (YAGNI)** | No se construye sync imposible; se entrega lo mínimo valioso (claridad + guía). Sin tablas ni endpoints nuevos. ✅ |

**Resultado**: PASS. (El re-alcance evita construir algo no soportado por la integración → más alineado con el principio V que la spec original.)

## Project Structure

### Documentation (this feature)

```text
specs/009-booking-offers/
├── plan.md
├── research.md           # Hallazgo: la API no gestiona deals de Booking
├── data-model.md         # Sin entidades nuevas (v1 informativa)
├── quickstart.md         # Cómo validar (chat + sección Ofertas)
├── contracts/
│   ├── offers-page.md     # Contrato de la sección "Ofertas" (UI + deep-links)
│   └── agent-guidance.md  # Comportamiento del agente ante deals de Booking
└── tasks.md               # (lo crea /speckit-tasks)
```

### Source Code (repository root)

```text
apps/web/
├── app/(app)/offers/page.tsx        # NUEVO — sección "Ofertas" (distinción + deep-links + guía)
├── components/layout/sidebar.tsx    # + ítem de menú "Ofertas"
└── lib/                             # config de enlaces (dashboard Beds24 / extranet Booking)

apps/api/
└── app/agent/prompts.py             # + regla: deals visibles de Booking se gestionan fuera (enlace);
                                      #   distinguir de la promoción de precio interna

apps/api/tests/
└── test_agent_orchestrator.py       # + caso: pedir "deal visible en Booking" → no crea promo interna
```

**Structure Decision**: feature mínima — una página informativa nueva en la web (con deep-links) y un ajuste del prompt del agente. No hay backend de ofertas (la API no lo soporta). Los enlaces al dashboard de Beds24 y al extranet de Booking son configurables (no secretos).

## Complexity Tracking

> Sin violaciones. El re-alcance reduce complejidad (no se construye integración inexistente).
