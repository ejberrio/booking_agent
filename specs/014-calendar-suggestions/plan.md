# Implementation Plan: Sugerencias de precio en el calendario + acción única "Aprobar y aplicar"

**Branch**: `014-calendar-suggestions` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-calendar-suggestions/spec.md`

## Summary

Fusionar aprobar+aplicar en una sola acción sobre el endpoint `apply` existente (que ya aprueba implícitamente al pasar proposed→applied), añadiéndole lo que hoy le falta: validación de estado (cierra el bug latente de doble aplicación), recorte de días pasados y error honesto 409 en conflicto. En la web, el calendario marca los días con sugerencias vigentes (merge client-side de la lista `proposed` ya disponible — sin tocar el endpoint de calendario) y un panel lateral permite resolverlas al clic. La página de Sugerencias pasa a dos botones ("Aprobar y aplicar" / "Rechazar") y el endpoint `approve` se retira limpiamente (su único consumidor era esa UI).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 + React 19 (web)
**Primary Dependencies**: FastAPI + SQLAlchemy 2.0 async + Alembic (API); Tailwind v4 + shadcn/ui + @tanstack/react-query + sonner (web)
**Storage**: PostgreSQL (prod) / SQLite async (tests). **Sin migraciones**: no cambia ningún modelo.
**Testing**: pytest (asyncio, dobles del Channel Manager — sin APIs reales); web se verifica con `npm run build`
**Target Platform**: Railway (web pública + api privada), CD al mergear a main
**Project Type**: monorepo web application (apps/api + apps/web)
**Performance Goals**: n/a (una propiedad, decenas de sugerencias a lo sumo)
**Constraints**: human-in-the-loop (Principio III): el detalle en pantalla es la previsualización y el clic la confirmación; estado local nunca miente ante fallo del canal (patrón SyncIssue); no romper los 174 tests
**Scale/Scope**: single-tenant, 1 propiedad, 1 unidad; ~6 archivos API + ~6 archivos web

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec → plan → tasks → analyze → implement; sin ADR nuevo (no hay decisión de arquitectura: se refina un flujo existente) |
| II. Provider-agnostic | ✅ la publicación sigue pasando por `pricing_app_service.set_day_price` → puerto ChannelManager; nada de Beds24 se filtra |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ la acción única NO elimina la confirmación: el host ve el detalle completo (precio sugerido vs actual, rango, confianza, racional) y confirma con el clic; lo que se elimina es un segundo clic redundante que no añadía información ni control. Auditoría intacta (`applied_change_id` → price_change_log, origin=suggestion). Fallo de canal → SyncIssue y estado honesto |
| IV. Tipado y pruebas en los límites | ✅ validación de estado y recorte de pasado con tests (es lógica que puede costar dinero); TS tipado en web |
| V. Simplicidad | ✅ sin modelos ni migraciones nuevas; endpoint `approve` retirado (menos superficie); marcado del calendario client-side sin tocar la API de calendario |

**Post-diseño (re-check)**: ✅ sin violaciones; no hay filas en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-calendar-suggestions/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── suggestions-api.md
└── tasks.md             # /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/
├── app/services/intelligence_service.py   # apply_suggestion: validación de estado + recorte de pasado + SyncIssue en fallo
├── app/services/suggestion_service.py     # sin cambios (approve queda como función interna/histórica)
├── app/api/routes/suggestions.py          # apply → 409 en conflicto de estado; approve RETIRADO
└── tests/test_suggestion_resolve.py       # NUEVO: estados, recorte, fallo de canal, doble aplicación

apps/web/
├── app/(app)/calendar/page.tsx            # query de sugerencias + panel de resolución
├── app/(app)/suggestions/page.tsx         # botón único (quita approve)
├── components/calendar/price-calendar.tsx # marcador de sugerencia + leyenda
├── components/calendar/suggestion-panel.tsx  # NUEVO: detalle + Aprobar y aplicar / Rechazar
├── components/suggestions/suggestion-card.tsx # dos botones
└── lib/api.ts                             # quita approveSuggestion; applySuggestion igual
```

**Structure Decision**: monorepo existente apps/api + apps/web; sin directorios nuevos salvo `suggestion-panel.tsx`.

## Decisiones clave (detalle en research.md)

1. **La acción combinada ES el endpoint `apply` reforzado** — `POST /suggestions/{id}/apply` ya publica y ya transiciona proposed→applied directamente; le falta seguridad, no semántica. Se añade: validación de estado (`proposed` o `approved` histórica; otra cosa → conflicto 409 con mensaje del estado real), recorte a días no pasados (FR-010), y SyncIssue + no-persistencia en fallo del canal (FR-003). No se crea endpoint nuevo.
2. **`POST /{id}/approve` se retira** — su único consumidor era el botón de la web que desaparece; mantenerlo "por compatibilidad" violaría el Principio V. `suggestion_service.approve` (función) se conserva: los tests históricos la usan y el estado `approved` sigue siendo entrada válida de `apply` (sugerencias aprobadas-sin-aplicar preexistentes, FR-011).
3. **Marcado del calendario client-side** — la página de calendario ya tiene react-query; añade `listSuggestions("proposed")` (query ya usada por dashboard/sugerencias, misma key = caché compartida) y computa `date → sugerencias vigentes` en el cliente. El endpoint `/pricing/calendar` no se toca (cero riesgo de regresión sobre FR-012/SC-005).
4. **Resolución desde el calendario en el panel lateral existente** — clic en un día = selección de un día (mecánica actual); si tiene sugerencias vigentes, el panel lateral muestra `SuggestionPanel` con el detalle completo y las dos acciones; soporta N sugerencias por día (lista). Tras resolver: invalidar queries `["suggestions"]` y `["calendar", ...]`.
5. **Conflicto de estado → HTTP 409** — el frontend muestra el `detail` del servidor y refresca; nunca segunda aplicación (SC-004).

## Fase 0 → research.md · Fase 1 → data-model.md, contracts/, quickstart.md

Sin NEEDS CLARIFICATION pendientes: las incógnitas eran (a) dónde vive la acción combinada, (b) fuente de datos del marcado, (c) destino de `approve` — resueltas arriba con el código existente como evidencia (ver research.md).
