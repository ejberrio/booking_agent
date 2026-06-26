# Contrato — Frontend web

## Mapa de rutas (App Router)

| Ruta | Pantalla | Acceso |
|------|----------|--------|
| `/login` | Contraseña del host | público |
| `/` | Dashboard | protegido |
| `/calendar` | Calendario de precios | protegido |
| `/chat` | Chat del agente | protegido |
| `/suggestions` | Bandeja de sugerencias | protegido |
| `/settings` | Configuración (LLM, integraciones) | protegido |
| `/onboarding` | Onboarding (conectar/importar/propiedad) | protegido |
| `POST /api/login` · `POST /api/logout` | Auth (route handlers) | — |

`middleware.ts` redirige a `/login` si no hay cookie de sesión válida (excepto `/login`, `/api/login`, assets).

## Cliente de API (`lib/api.ts`) ↔ endpoints

| Función | Endpoint backend |
|---------|------------------|
| `getCalendar(unitTypeId, from, to)` | `GET /pricing/calendar` |
| `previewRange(req)` | `POST /pricing/range/preview` |
| `applyRange(req)` | `POST /pricing/range/apply` |
| `setDay(req)` | `POST /pricing/day` |
| `getHistory(...)` | `GET /pricing/history` |
| `createPromotion(...)` / `deletePromotion(id)` | `POST/DELETE /pricing/promotions` |
| `listSuggestions(status?)` | `GET /suggestions` |
| `approve/reject/applySuggestion(id)` | `POST /suggestions/{id}/...` |
| `sendChat(message, conversationId?)` | `POST /chat` |
| `streamChat(...)` (SSE) | `POST /chat/stream` |
| `testConnection()` / `importRemote()` / `listRuns()` / `listIssues()` | `/sync/*` |

Todas las funciones son tipadas (`lib/types.ts`) y se usan vía hooks de React Query.

## Garantías de comportamiento (UI)

- **G1**: las rutas de la app requieren sesión; sin cookie → `/login`.
- **G2**: toda escritura de precio muestra preview (diff) y exige confirmación; `stale` → re-previsualiza (G de FR-004/FR-005).
- **G3**: el chat transmite por SSE y muestra Confirmar/Cancelar en las propuestas; cancelar no aplica nada.
- **G4**: sugerencias se listan con justificación/confianza; aprobar/rechazar/aplicar llaman a la API.
- **G5**: dashboard muestra ocupación/heatmap/eventos/sugerencias (sin ingresos en v1), con estados de carga/vacío.
- **G6**: errores de backend → estado claro + reintentar; ningún secreto se muestra.
- **G7**: calendario y chat usables en móvil (responsive).

## Verificación

- `npm run build` (typecheck + lint de `next build`) en `apps/web` debe pasar **sin errores**. Es el criterio de aceptación de esta feature.
- Demostración manual de los flujos clave contra el backend (o datos simulados): calendario → preview → confirmar; chat → propuesta → confirmar; sugerencias → aplicar.
