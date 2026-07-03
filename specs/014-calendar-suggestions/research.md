# Research: Feature 014 — Sugerencias en el calendario + acción única

**Date**: 2026-07-03 · Método: lectura del código existente (sin incógnitas externas: no hay API nueva de terceros).

## R1. ¿Dónde vive la acción combinada "Aprobar y aplicar"?

- **Decision**: reforzar el endpoint existente `POST /suggestions/{id}/apply` — no crear uno nuevo.
- **Rationale**: la lectura de `intelligence_service.apply_suggestion` muestra que HOY ya hace la semántica combinada (aplica precios día a día vía `pricing_app_service.set_day_price` con `origin=suggestion`, enlaza `applied_change_id` y pasa la sugerencia directamente a `applied` desde cualquier estado). Lo que le falta es seguridad, no semántica:
  1. **No valida el estado** → una sugerencia ya `applied` o `rejected` puede re-aplicarse (bug latente de doble aplicación que la feature cierra — FR-009/SC-004).
  2. **No recorta días pasados** → aplicaría precios a fechas ya transcurridas (FR-010).
  3. **No registra SyncIssue en fallo del canal**; hay que verificar el comportamiento de `set_day_price` ante fallo y garantizar que la sugerencia no queda `applied` si no se publicó (FR-003) — al ser todo una misma transacción de sesión que solo se comitea en la ruta, un raise antes del commit ya deja el estado local intacto; falta la incidencia visible.
- **Alternatives considered**: endpoint nuevo `POST /{id}/resolve` (más superficie, mismo comportamiento — rechazado por Principio V); parámetro `mode` en apply (complejidad sin caso de uso).

## R2. ¿Qué pasa con `POST /{id}/approve` y el estado `approved`?

- **Decision**: retirar la ruta `approve` de la API y el botón de la UI; conservar `suggestion_service.approve` como función y `approved` como estado válido de entrada de `apply`.
- **Rationale**: grep de consumidores: la ruta solo la llamaba `api.approveSuggestion` de la web (botón que desaparece); el agente de chat solo usa `list_suggestions`. Mantener una ruta muerta contradice el Principio V. El estado `approved` NO se puede retirar: existen (o pueden existir) sugerencias aprobadas-sin-aplicar previas al cambio que deben seguir siendo resolubles (FR-011) — `apply` acepta `proposed` y `approved`; `reject` sigue aceptando solo `proposed` como hoy (una `approved` histórica se resuelve aplicándola; caso marginal aceptado y documentado).

  **Corrección durante el diseño**: para no dejar huérfanas las `approved` históricas también en el rechazo, `reject` pasará a aceptar `proposed` y `approved`. Es un cambio de una línea con test propio y mantiene la simetría "toda sugerencia no resuelta es resoluble en ambos sentidos".
- **Alternatives considered**: deprecación blanda (ruta que responde 410) — innecesaria sin consumidores externos; retirar también el estado `approved` (rompería filas históricas y exigiría migración de datos — rechazado).

## R3. ¿De dónde salen los datos para marcar el calendario?

- **Decision**: merge client-side. La página de calendario añade la query `["suggestions"]` → `GET /suggestions?status=proposed` (misma queryKey que dashboard/página de sugerencias = caché compartida de react-query) y computa en el cliente el mapa `fecha → sugerencias vigentes` (vigente = `proposed` y `date_to >= hoy`).
- **Rationale**: el endpoint `/pricing/calendar` construye su vista día a día con consultas por día; inyectarle sugerencias lo acoplaría al modelo de mercado y arriesgaría regresiones en un endpoint que la spec exige intacto (SC-005/FR-012). La lista de sugerencias es pequeña (decenas), el cruce por fecha es trivial en el cliente y el dato ya viaja a la web para la página de Sugerencias.
- **Alternatives considered**: extender `CalendarDayView` server-side (acoplamiento + riesgo de regresión, rechazado); endpoint nuevo `suggestions/by-day` (superficie innecesaria).

## R4. ¿Cómo se marca y se resuelve en la UI del calendario?

- **Decision**: `PriceCalendar` recibe una prop opcional `suggestionDates: Set<string>` y pinta un punto violeta (`bg-violet-500`) junto a los puntos existentes (promoción=ámbar, bloqueada=gris, reservada=rojo) + entrada en la leyenda. El clic reutiliza la mecánica de selección actual (un clic = selección de un día); si el día seleccionado tiene sugerencias vigentes, el panel lateral (columna donde ya viven RangeEditor y "Precio por canal") muestra el nuevo `SuggestionPanel`: por cada sugerencia del día — precio sugerido vs precio efectivo actual del día, rango completo, confianza, racional y botones "Aprobar y aplicar" / "Rechazar".
- **Rationale**: cero cambios a la mecánica de drag-selección (que la Mejora A/#94 también reutilizará); los marcadores conviven porque son puntos independientes (edge case de convivencia cubierto por construcción); popover flotante descartado porque el panel lateral ya es el patrón de la página para "detalle de lo seleccionado".
- **Alternatives considered**: popover anclado al día (nuevo patrón de UI + problemas de espacio en móvil); página intermedia (rompe el "sin salir del calendario").

## R5. Manejo de conflicto de estado y fallo de canal (contrato de errores)

- **Decision**:
  - Estado no aplicable (`applied`/`rejected`, o vencida total) → **HTTP 409** con `detail` honesto que incluye el estado real (hoy `apply` devuelve 404 para todo ValueError; se separa: 404 solo si no existe).
  - Fallo de publicación al canal → la excepción del puerto se captura, se registra `SyncIssue` (patrón de `channel_pricing_service`), rollback implícito (sin commit) y **HTTP 502/422 con mensaje claro**; la sugerencia sigue `proposed`.
  - Frontend: `onError` muestra el `detail` del servidor (toast) e invalida `["suggestions"]` y `["calendar"]` SIEMPRE (éxito o conflicto) para refrescar el estado real.
- **Rationale**: FR-003/FR-009; mismo patrón de honestidad ya usado en offsets (feature 013).

## R6. Recorte de días pasados (FR-010)

- **Decision**: en `apply_suggestion`, `effective_from = max(date_from, hoy)`; si `date_to < hoy` → 409 "vencida" sin cambios. La respuesta incluye `applied_from` para que la UI comunique "aplicada desde hoy" cuando hubo recorte. La definición de "hoy" usa la fecha local del servidor (igual que el resto del sistema).
- **Rationale**: nunca simular cambios del pasado; el canal manager rechazaría/ignoraría fechas pasadas de todos modos y el estado local mentiría.
- **Alternatives considered**: pedir confirmación extra ante recorte (fricción sin valor: el efecto se comunica y es el único posible).
