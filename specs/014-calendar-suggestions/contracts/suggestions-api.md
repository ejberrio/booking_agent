# Contract: API de sugerencias — acción única y errores honestos

**Feature**: 014-calendar-suggestions

## `GET /suggestions` (extendido, retrocompatible)

- Cada elemento gana **`current_price`**: precio base vigente del primer día no pasado del rango (`null` si no hay precio) — es el "vs actual" de la previsualización informada (FR-004) en ambas superficies.
- Parámetro nuevo opcional **`pending=true`**: devuelve `proposed` + `approved` (las pendientes de resolver, remediación C1); `status=` puntual sigue funcionando igual.

```json
[
  {
    "id": 7,
    "unit_type_id": 1,
    "date_from": "2026-09-10",
    "date_to": "2026-09-12",
    "suggested_price": "380000.00",
    "current_price": "350000.00",
    "rationale": {"text": "Concierto en el Daviarena"},
    "confidence": "0.800",
    "status": "proposed"
  }
]
```

Consumidores: dashboard, página de Sugerencias y calendario pasan a `pending=true` (el calendario solo marca las `proposed`; una `approved` histórica ya fue decidida).

## `POST /suggestions/{id}/apply` — ahora "Aprobar y aplicar" (reforzado)

Una sola operación: valida → aplica precios (solo días no pasados) → publica → audita → `applied`.

- **200**: sugerencia serializada como hoy **+ `applied_from`** (primer día realmente aplicado; igual a `date_from` si no hubo recorte):

```json
{ "id": 7, "status": "applied", "applied_from": "2026-09-10", "...": "resto igual que hoy" }
```

- **404**: no existe la sugerencia.
- **409** (conflicto honesto, sin efectos):
  - ya resuelta: `{"detail": "La sugerencia ya está aplicada (estado real: applied)"}` — cubre la doble aplicación y la resolución concurrente.
  - vencida: `{"detail": "La sugerencia venció (rango 2026-06-01 → 2026-06-05, todo en el pasado)"}`.
- **502**: la publicación al canal falló → `SyncIssue` registrada, estado local intacto (`proposed`), `detail` con el motivo.

Estados de entrada válidos: `proposed` y `approved` (históricas aprobadas-sin-aplicar).

## `POST /suggestions/{id}/reject` (ajuste mínimo)

Acepta `proposed` **y** `approved` (antes solo `proposed`); resto igual. 409 si ya está `applied`/`rejected` (hoy devuelve 400 — se unifica con apply en 409; único consumidor: la web).

## `POST /suggestions/{id}/approve` — RETIRADO

Se elimina la ruta (consumidor único: botón de la web que desaparece). `suggestion_service.approve` se conserva como función interna y `approved` sigue siendo estado válido de entrada para apply/reject.

## Web (contratos de UI)

- `lib/api.ts`: se elimina `approveSuggestion`; `applySuggestion`/`rejectSuggestion` sin cambios de firma; `Suggestion` gana `applied_from?: string` (solo en la respuesta de apply).
- `PriceCalendar` (componente): prop nueva **opcional** `suggestionDates?: Set<string>` — sin ella, render idéntico al actual (FR-012).
- `SuggestionPanel` (nuevo): recibe las sugerencias vigentes del día seleccionado + precio efectivo actual del día; muestra por sugerencia: sugerido vs actual, rango, confianza %, racional, botones "Aprobar y aplicar" / "Rechazar"; toasts con el `detail` del servidor en error; invalida `["suggestions"]` y `["calendar"]` al terminar (éxito o conflicto).
- `SuggestionCard` (lista): dos botones — "Aprobar y aplicar" (primario) y "Rechazar"; desaparece "Aprobar".

## Criterios de aceptación

- Aplicar dos veces la misma sugerencia: la segunda devuelve 409 y NO produce un segundo cambio de precio (SC-004).
- Sugerencia parcialmente vencida: solo los días `>= hoy` reciben precio; `applied_from` lo refleja y la UI lo comunica (FR-010).
- Fallo del canal: sugerencia sigue `proposed`, `SyncIssue` visible (FR-003).
- Sin sugerencias vigentes: calendario y respuestas byte-a-byte como hoy (FR-012, SC-005).
