# Research — Frontend web

Formato: Decisión / Justificación / Alternativas.

## 1. Capa de datos → TanStack Query

- **Decisión**: `@tanstack/react-query` para fetching, caché, estados de carga/error y revalidación.
- **Justificación**: Estados de carga/vacío/error consistentes (FR-013) con poco código; estándar.
- **Alternativas**: fetch + useState manual (más boilerplate); SWR (equivalente).

## 2. Autenticación → contraseña única (servidor de la web)

- **Decisión**: Pantalla `/login` → `POST /api/login` (route handler de Next) valida contra `APP_PASSWORD` (env del servidor, NO `NEXT_PUBLIC_*`); si coincide, set cookie httpOnly. `middleware.ts` protege todas las rutas excepto `/login` y `/api/login`. `POST /api/logout` limpia la cookie.
- **Justificación**: Clarificación (contraseña única, validada en el servidor web, sin tocar FastAPI). Simple y suficiente para single-tenant.
- **Alternativas**: sin auth (expuesto al desplegar); magic link (requiere email; excesivo).

## 3. Streaming del chat → lector de SSE sobre fetch

- **Decisión**: `lib/sse.ts` hace `POST /chat/stream` y lee el `ReadableStream` de la respuesta, parseando eventos SSE (`event: tool` / `event: done`). La UI muestra el estado de herramientas y, al `done`, el texto y (si hay) la propuesta con Confirmar/Cancelar.
- **Justificación**: El backend ya expone SSE; `fetch` + reader funciona con POST (a diferencia de `EventSource`, que es solo GET).
- **Alternativas**: `EventSource` (no soporta POST/cuerpo); polling (peor UX).

## 4. Calendario de precios → grid propio + heatmap

- **Decisión**: Componente de mes propio (grilla 7×N) que pinta cada día con color según el precio (heatmap), muestra base/efectivo, disponibilidad y badges de promo/evento; selección de rango con eventos de puntero (clic + arrastrar).
- **Justificación**: Control total del UX (lo opuesto a la Extranet); evita dependencias pesadas de calendario.
- **Alternativas**: librería de calendario (rígida para este caso); tabla simple (peor visual).

## 5. Preview → confirmación (escrituras)

- **Decisión**: `range-editor` llama `/pricing/range/preview` → muestra el diff (días, antes→nuevo, inválidos señalados) en un diálogo → al confirmar llama `/pricing/range/apply` con el `fingerprint`. Si la respuesta es `stale`, vuelve a previsualizar.
- **Justificación**: Human-in-the-loop visible (FR-004/FR-005); reutiliza el flujo del backend (no duplica lógica).
- **Alternativas**: aplicar directo (viola III).

## 6. Notificaciones → sonner

- **Decisión**: `sonner` para toasts (sugerencias nuevas, errores de sync, confirmaciones).
- **Justificación**: Integra con shadcn; ligero.
- **Alternativas**: toaster propio (reinventar).

## 7. Tema claro/oscuro → next-themes

- **Decisión**: `next-themes` con estrategia de clase; Tailwind v4 en modo oscuro por clase. Toggle en el shell.
- **Justificación**: Estándar, sin parpadeo; cumple FR-001.
- **Alternativas**: manejo manual de clase (más frágil).

## 8. Formato de moneda y fechas

- **Decisión**: `Intl.NumberFormat('es-CO', {currency:'COP'})` para precios; `date-fns` para fechas/calendario.
- **Justificación**: Localización correcta (COP, Medellín); utilidades probadas.

## 9. Verificación

- **Decisión**: `npm run build` (que en Next ejecuta typecheck + lint) es el gate de esta feature. No se añade infra de unit/e2e.
- **Justificación**: Cubre tipos y lint; a esta escala el costo/beneficio de e2e no se justifica aún (se puede añadir en Fase 7).
- **Alternativas**: Vitest + Testing Library / Playwright (se aplazan).

## Sin NEEDS CLARIFICATION pendientes

Auth (contraseña única), alcance (todas las pantallas) e ingresos (aplazados) se resolvieron en `/speckit-clarify`.
