---
description: "Task list — Ofertas de Booking.com (v1 ligera: guía + claridad)"
---

# Tasks: Ofertas de Booking.com (v1 ligera)

**Input**: Design documents from `/specs/009-booking-offers/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Contexto**: el plan halló (verificado en vivo) que la API de Beds24 V2 NO gestiona los deals de Booking. v1 = **claridad del agente** + **sección "Ofertas" informativa con deep-links** (sin sync, sin endpoints, sin entidades nuevas).

**Tests**: solo el del comportamiento del agente (Constitución IV: evita que el agente confunda/cree algo equivocado).

**Organization**: por historia — US1 (claridad del agente, P1), US2 (sección Ofertas, P1), US3 (distinción/verificación, P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivos distintos, sin dependencias. Monorepo: `apps/web/`, `apps/api/`.

---

## Phase 1: Setup

- [X] T001 [P] Definir la config de enlaces (dashboard Beds24 → Channel Manager → Booking.com → Promotions, y extranet de Booking) como constantes en `apps/web/lib/links.ts` (no secretos)

---

## Phase 2: Foundational (Blocking Prerequisites)

> Sin tareas: v1 es informativa; no hay infraestructura/backend compartido nuevo (la API no expone ofertas). Se procede directo a las historias.

---

## Phase 3: User Story 1 - Claridad del agente (Priority: P1) 🎯 MVP

**Goal**: Ante una solicitud de "promoción visible en Booking", el agente explica que esos deals se gestionan en Beds24/Booking (con enlace) y NO crea una promoción de precio interna por error; "bajar el precio" → promoción interna; ambiguo → pregunta.

**Independent Test**: "crea una promoción que se vea en Booking" → respuesta deriva a Beds24/Booking, sin crear `AgentAction`; "baja el precio 10% en septiembre" → propone promoción de precio interna.

- [X] T002 [US1] Añadir la regla en `apps/api/app/agent/prompts.py`: distinguir "Ofertas de Booking" (visibles, se gestionan en Beds24/Booking → explicar y enlazar, NO crear promo interna) de "Promociones de precio internas" (`propose_create_promotion`); ante ambigüedad, preguntar
- [X] T003 [US1] Test en `apps/api/tests/test_agent_orchestrator.py`: "promoción visible en Booking" → no se crea `AgentAction`; "baja el precio 10%…" → propone promoción interna

**Checkpoint**: el agente enruta correctamente las dos clases de descuento.

---

## Phase 4: User Story 2 - Sección "Ofertas" en la web (Priority: P1)

**Goal**: Una sección dedicada que explica la distinción y enlaza al dashboard de Beds24 y al extranet de Booking, con un mini-instructivo.

**Independent Test**: abrir "Ofertas" en el menú lateral → ver la distinción, los enlaces (abren en pestaña nueva) y el instructivo; `npm run build` verde.

- [X] T004 [US2] Crear la página `apps/web/app/(app)/offers/page.tsx`: explicación de "Ofertas de Booking" (visibles, externas) vs "Promociones de precio internas" (de la app), deep-links (de `lib/links.ts`) al dashboard de Beds24 y al extranet de Booking, y un mini-instructivo de pasos
- [X] T005 [US2] Añadir el ítem "Ofertas" al menú lateral en `apps/web/components/layout/sidebar.tsx` (array `NAV`, con icono)
- [X] T006 [US2] `npm run build` verde en `apps/web` (la página y el menú compilan)

**Checkpoint**: la sección "Ofertas" guía al host a crear los deals en Beds24/Booking.

---

## Phase 5: User Story 3 - Distinción coherente (Priority: P2)

**Goal**: La nomenclatura es consistente y sin ambigüedad entre la página, el chat y el resto de la app.

**Independent Test**: revisar que "Ofertas de Booking" vs "Promociones de precio internas" se nombran igual en la página y en los mensajes del agente; un enlace desde "Ofertas" lleva a la promoción interna (en chat/calendario) cuando corresponde.

- [X] T007 [US3] Verificar y unificar la nomenclatura ("Ofertas de Booking" / "Promociones de precio internas") en `apps/web/app/(app)/offers/page.tsx` y en `apps/api/app/agent/prompts.py`; enlazar desde la página a la gestión de promociones internas (chat/calendario)

**Checkpoint**: el host no confunde las dos clases de descuento.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T008 Ejecutar `uv run ruff check . && uv run pytest` (api) y `npm run build` (web) — todo verde
- [X] T009 Validar `quickstart.md`: el chat enruta bien las dos solicitudes y la página "Ofertas" carga con enlaces correctos (verificación en vivo vía el proxy con cookie de sesión)

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: T001 (config de enlaces) antes de la página (T004).
- **US1 (Phase 3)** y **US2 (Phase 4)**: independientes entre sí (backend agente vs frontend) → pueden ir en paralelo.
- **US3 (Phase 5)**: tras US1+US2 (coherencia de nomenclatura).
- **Polish (Phase 6)**: al final.

## Parallel Opportunities

- US1 (prompt+test del agente) ‖ US2 (página+menú) en paralelo.
- T001 (links) es prerrequisito de T004.

## Implementation Strategy

### MVP
1. T001 (links) → US1 (claridad del agente) + US2 (sección Ofertas).
2. Validar: el agente no confunde las dos clases; la página guía a Beds24/Booking.

### Notas
- Sin entidades, sin endpoints, sin migraciones (la API no expone deals).
- Constitución V (YAGNI): se evita construir una integración inexistente; se entrega lo mínimo valioso.
- Si más adelante se evalúa otro Channel Manager con Promotions API (p. ej. Channex), sería otra feature.
