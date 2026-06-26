# Implementation Plan: Frontend web (UX / dashboard)

**Branch**: `006-web-frontend` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/006-web-frontend/spec.md`

## Summary

Interfaz web en Next.js (`apps/web`, sobre el scaffold existente) que consume la API FastAPI ya construida y ofrece una UX intuitiva: **calendario de precios interactivo** (seleccionar/arrastrar → previsualizar diff → confirmar), **chat del agente** con streaming SSE y confirmación visible, **bandeja de sugerencias** (aprobar/rechazar/aplicar), **dashboard** (ocupación, heatmap, eventos, sugerencias; ingresos aplazados), **onboarding + configuración** (conectar Beds24, importar, ajustes de LLM, estado de integraciones) y **notificaciones**. Acceso protegido por una **contraseña única del host** validada en el servidor de la web (Next.js + cookie httpOnly), sin tocar el backend. Verificación = build de producción (typecheck + lint).

## Technical Context

**Language/Version**: TypeScript 5 / Next.js 15 (App Router), Node ≥ 20  
**Primary Dependencies**: React 19, Tailwind v4 + shadcn/ui (ya en el scaffold), `@tanstack/react-query` (datos), `sonner` (toasts), `date-fns` (fechas), `lucide-react`, `next-themes` (modo claro/oscuro)  
**Storage**: ninguno propio (estado de UI + caché de React Query); datos en el backend  
**Testing**: `npm run build` (typecheck + lint de `next build`) como verificación; no se añade infra de unit/e2e en esta feature  
**Target Platform**: Navegador (desktop + móvil); servida por Next.js  
**Project Type**: Web (frontend; consume la API existente)  
**Integration**: API FastAPI (`/sync`, `/pricing`, `/chat` + SSE `/chat/stream`, `/suggestions`) vía `NEXT_PUBLIC_API_URL`  
**Constraints**: human-in-the-loop visible (preview + confirmación en toda escritura); sin exponer secretos; estados de carga/vacío/error; responsive; sin reimplementar lógica de negocio  
**Scale/Scope**: 1 host; pocas propiedades; volumen pequeño

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| I. Spec-Driven | Procede de spec.md (006) con clarificaciones. ✅ |
| II. Provider-agnostic | El frontend consume la API; no incrusta lógica de proveedor; toda integración pasa por el backend. ✅ |
| III. Human-in-the-loop | Preview + confirmación visibles en calendario y chat; nada se aplica sin confirmar. ✅ |
| IV. Tipado y pruebas | TypeScript estricto; verificación por `next build` (typecheck+lint). *(Unit/e2e UI se aplazan; justificado: la build cubre tipos/lint y el riesgo de regresión es bajo a esta escala.)* ✅ |
| V. Simplicidad | Reutiliza el scaffold; dependencias mínimas y estándar; sin estado global pesado. ✅ |

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/006-web-frontend/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── frontend-contract.md   # mapa de páginas/rutas + cliente de API + auth + verificación
├── quickstart.md
└── tasks.md
```

### Source Code (apps/web)

```text
apps/web/
├── middleware.ts                       # gate de auth (cookie httpOnly)
├── app/
│   ├── api/login/route.ts              # POST: valida APP_PASSWORD (env servidor) → cookie
│   ├── api/logout/route.ts
│   ├── login/page.tsx                  # pantalla de contraseña
│   ├── (app)/layout.tsx                # shell: sidebar, providers, tema
│   ├── (app)/page.tsx                  # Dashboard
│   ├── (app)/calendar/page.tsx         # Calendario de precios
│   ├── (app)/chat/page.tsx             # Chat del agente
│   ├── (app)/suggestions/page.tsx      # Bandeja de sugerencias
│   ├── (app)/settings/page.tsx         # Configuración (LLM, integraciones)
│   └── (app)/onboarding/page.tsx       # Onboarding (conectar/importar/propiedad)
├── components/
│   ├── ui/                             # shadcn: button (existe) + card, dialog, input, badge, skeleton, label
│   ├── providers.tsx                   # QueryClientProvider + Toaster + ThemeProvider
│   ├── layout/sidebar.tsx, theme-toggle.tsx
│   ├── calendar/price-calendar.tsx     # grid mensual + heatmap + selección de rango
│   ├── calendar/range-editor.tsx       # editar precio → preview (diff) → confirmar
│   ├── chat/chat-panel.tsx             # SSE + propuestas con Confirmar/Cancelar
│   ├── suggestions/suggestion-card.tsx
│   └── dashboard/*.tsx                 # KPIs, heatmap, eventos, sugerencias pendientes
└── lib/
    ├── api.ts                          # cliente tipado (extiende el actual)
    ├── sse.ts                          # lector de SSE para /chat/stream
    └── types.ts                        # tipos de las respuestas de la API
```

**Structure Decision**: Se construye sobre el scaffold (`apps/web`, Tailwind v4 + shadcn). Rutas con App Router agrupadas en `(app)` tras el gate de auth (`middleware.ts` + route handler que valida `APP_PASSWORD` del servidor). Datos vía `@tanstack/react-query` contra un cliente tipado (`lib/api.ts`). El frontend NO duplica lógica; toda escritura usa el flujo preview→apply del backend.

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
