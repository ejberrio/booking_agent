---
description: "Task list — Frontend web (UX/dashboard)"
---

# Tasks: Frontend web (UX / dashboard)

**Input**: Design documents from `specs/006-web-frontend/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/frontend-contract.md

**Tests**: Verificación de esta feature = **`npm run build`** (typecheck + lint de `next build`). No se añaden tests unitarios/e2e (se aplazan a Fase 7).

**Organización**: por historia (US1–US6). Trabajo en `apps/web`. Consume la API existente; no duplica lógica.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivo distinto, sin dependencias pendientes.
- **[Story]**: US1–US6.

---

## Phase 1: Setup

- [ ] T001 Instalar dependencias (`@tanstack/react-query`, `sonner`, `date-fns`, `next-themes`) en `apps/web/package.json`
- [ ] T002 [P] Añadir componentes base de shadcn/ui (card, dialog, input, badge, skeleton, label, select) en `apps/web/components/ui/`
- [ ] T003 [P] Utilidades de formato (COP con `Intl.NumberFormat`, fechas con date-fns) en `apps/web/lib/format.ts`

---

## Phase 2: Foundational (API, auth, shell)

**⚠️ Bloqueante para todas las historias.**

- [ ] T004 [P] Tipos de la API en `apps/web/lib/types.ts`
- [ ] T005 Cliente de API tipado (pricing, suggestions, chat, sync) en `apps/web/lib/api.ts` (extiende el actual)
- [ ] T006 [P] Lector de SSE para `/chat/stream` en `apps/web/lib/sse.ts`
- [ ] T007 [P] Providers (`QueryClientProvider` + `Toaster` de sonner + `ThemeProvider`) en `apps/web/components/providers.tsx`
- [ ] T008 Auth por contraseña: `apps/web/middleware.ts` + `apps/web/app/api/login/route.ts` + `apps/web/app/api/logout/route.ts` + `apps/web/app/login/page.tsx` (valida `APP_PASSWORD`, cookie httpOnly)
- [ ] T009 Shell de la app: `apps/web/app/(app)/layout.tsx` + `apps/web/components/layout/sidebar.tsx` + `apps/web/components/layout/theme-toggle.tsx`

**Checkpoint**: login, navegación y datos listos.

---

## Phase 3: User Story 1 - Calendario de precios interactivo (Priority: P1) 🎯 MVP

**Goal**: Ver precios por día (heatmap), seleccionar un rango, previsualizar el diff y confirmar.

**Independent Test**: Abrir `/calendar`, seleccionar un rango, escribir un precio, ver el diff y confirmar; el calendario se actualiza.

### Implementation for User Story 1

- [ ] T010 [US1] `PriceCalendar` (grid mensual + heatmap + badges promo/evento + selección de día/rango por arrastre) en `apps/web/components/calendar/price-calendar.tsx`
- [ ] T011 [US1] `RangeEditor` (precio → `/pricing/range/preview` → diálogo de diff con inválidos señalados → `/pricing/range/apply`; si `stale`, re-previsualiza) en `apps/web/components/calendar/range-editor.tsx`
- [ ] T012 [US1] Página `/calendar` (carga `get_calendar`, integra calendario + editor, estados de carga/vacío/error) en `apps/web/app/(app)/calendar/page.tsx`

**Checkpoint**: gestión de precios visual con preview+confirmación (MVP).

---

## Phase 4: User Story 2 - Chat del agente (Priority: P1)

**Goal**: Chat con streaming SSE, estado de herramientas y propuestas con Confirmar/Cancelar.

**Independent Test**: Pedir un cambio por chat, ver la propuesta con Confirmar; confirmar y ver el resultado.

### Implementation for User Story 2

- [ ] T013 [US2] `ChatPanel` (envía a `/chat/stream`, muestra streaming + estado de tools + propuesta con Confirmar/Cancelar) en `apps/web/components/chat/chat-panel.tsx`
- [ ] T014 [US2] Página `/chat` en `apps/web/app/(app)/chat/page.tsx`

**Checkpoint**: conversación agéntica con confirmación visible.

---

## Phase 5: User Story 3 - Bandeja de sugerencias (Priority: P2)

**Goal**: Listar sugerencias con justificación/confianza y aprobar/rechazar/aplicar.

**Independent Test**: Abrir `/suggestions`, aplicar una y ver el precio actualizado; rechazar otra.

### Implementation for User Story 3

- [ ] T015 [US3] `SuggestionCard` + lista (justificación, confianza, día/rango, acciones) en `apps/web/components/suggestions/suggestion-card.tsx`
- [ ] T016 [US3] Página `/suggestions` (carga `GET /suggestions`, acciones approve/reject/apply) en `apps/web/app/(app)/suggestions/page.tsx`

**Checkpoint**: "qué te propongo" accionable.

---

## Phase 6: User Story 4 - Dashboard (Priority: P2)

**Goal**: Panorama: ocupación, heatmap, eventos próximos y sugerencias pendientes (sin ingresos en v1).

**Independent Test**: Abrir `/` y ver los widgets; con datos vacíos, estados vacíos claros.

### Implementation for User Story 4

- [ ] T017 [P] [US4] Widgets del dashboard (KPI ocupación, mini-heatmap, eventos, sugerencias pendientes) en `apps/web/components/dashboard/`
- [ ] T018 [US4] Página `/` (dashboard) que compone los widgets, con carga/vacío en `apps/web/app/(app)/page.tsx`

**Checkpoint**: panorama de un vistazo.

---

## Phase 7: User Story 5 - Onboarding y configuración (Priority: P2)

**Goal**: Conectar Beds24, importar y elegir propiedad; ajustar LLM y ver estado de integraciones.

**Independent Test**: Completar onboarding (conectar→importar→propiedad); cambiar el modelo de LLM en Configuración.

### Implementation for User Story 5

- [ ] T019 [US5] Página `/onboarding` (prueba de conexión `/sync/test`, importar `/sync/import`, seleccionar propiedad, estado de sync) en `apps/web/app/(app)/onboarding/page.tsx`
- [ ] T020 [US5] Página `/settings` (config de LLM, estado de integraciones, sin mostrar secretos) en `apps/web/app/(app)/settings/page.tsx`

**Checkpoint**: arranque y ajustes.

---

## Phase 8: User Story 6 - Notificaciones y responsive (Priority: P3)

**Goal**: Avisos de sugerencias/errores y buena experiencia en móvil.

**Independent Test**: Provocar un error de sync → toast; abrir en móvil → calendario y chat usables.

### Implementation for User Story 6

- [ ] T021 [US6] Toasts (sonner) para sugerencias nuevas y errores de sync, integrados en los hooks de datos, en `apps/web/lib/api.ts` / `apps/web/components/providers.tsx`
- [ ] T022 [US6] Pasada responsive (sidebar colapsable en móvil; calendario y chat usables en pantalla estrecha) en `apps/web/components/layout/sidebar.tsx` y vistas

**Checkpoint**: conveniencia y movilidad.

---

## Phase 9: Polish & Cross-Cutting

- [ ] T023 [P] Estados de carga (skeleton) / vacío / error consistentes y actualizar `apps/web/README.md`
- [ ] T024 `npm run build` (typecheck + lint) en verde en `apps/web`

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2: API + auth + shell)** bloquea las historias.
- **US1 (P1, MVP)**: calendario (preview/confirmar).
- **US2 (P1)**: chat SSE.
- **US3 (P2)**: sugerencias. **US4 (P2)**: dashboard. **US5 (P2)**: onboarding/config.
- **US6 (P3)**: notificaciones + responsive (sobre todas).

### Dentro de cada historia
- Componentes → página que los compone.

### Paralelismo
- Setup: T002, T003 en paralelo. Foundational: T004, T006, T007 en paralelo (T005 cliente API y T008/T009 auth/shell tras los tipos).
- Componentes de historias distintas (archivos distintos) pueden ir en paralelo una vez lista la base; las páginas dependen de sus componentes.

---

## Implementation Strategy

### MVP primero (US1)
Setup → Foundational → US1 (calendario) → `npm run build` → demo.

### Entrega incremental
US1 (calendario) → US2 (chat) → US3 (sugerencias) → US4 (dashboard) → US5 (onboarding/config) → US6 (notificaciones/responsive). Verificar la build tras cada historia.

## Notes
- `[P]` = archivos distintos, sin dependencias pendientes.
- Verificación = `npm run build` (typecheck + lint). El frontend consume la API; no duplica lógica.
- Toda escritura de precio pasa por preview + confirmación (reusa `/pricing/range/preview` y `/apply`).
- Secretos nunca se muestran; `APP_PASSWORD` solo en el servidor (no `NEXT_PUBLIC_*`).
