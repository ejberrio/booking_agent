# Data Model — Frontend web

El frontend no posee datos de dominio; consume los del backend. Aquí se documentan los **tipos de la API** (en `lib/types.ts`) y el **estado de UI**.

## Tipos de la API (consumidos)

- **CalendarDayView**: `{ date, base_price, effective_price, available, promotions[] }` (de `GET /pricing/calendar`).
- **ChangePreview**: `{ items: [{date, old_price, new_price, valid, reason}], fingerprint, has_invalid, valid_count, invalid_count }` (de `POST /pricing/range/preview`).
- **ApplyResult**: `{ applied_days[], skipped_invalid[], audited, published, publish_issues, stale }` (de `POST /pricing/range/apply`).
- **Suggestion**: `{ id, unit_type_id, date_from, date_to, suggested_price, rationale, confidence, status }` (de `GET /suggestions`).
- **ChatReply**: `{ reply, conversation_id, pending_action_id, applied }` (de `POST /chat`); eventos SSE de `/chat/stream` (`tool`, `done`).
- **SyncStatus/Runs/Issues**: de `/sync/*` (estado de conexión/import).

## Estado de UI (no persistido)

- **HostSession**: autenticado (cookie) + propiedad/unidad activa seleccionada.
- **CalendarView**: `{ month, unitTypeId, selection: {from, to} | null }`.
- **ChangeDraft**: `{ selection, newPrice, preview?: ChangePreview }` — borrador antes de confirmar; conserva el `fingerprint` para la aplicación.
- **ChatThread**: lista de mensajes (rol, texto), `pendingActionId`, estado de streaming.

## Reglas / invariantes (UI)
1. Toda escritura pasa por `ChangeDraft` → preview visible → confirmación; nunca se aplica sin confirmar.
2. Si `ApplyResult.stale` o `ChangePreview` cambió, se re-previsualiza (no se aplica).
3. Los días inválidos del preview se muestran señalados y no se incluyen al aplicar.
4. Los precios se muestran formateados en COP; las fechas con locale es-CO.
5. Ningún secreto (API keys) se renderiza; Configuración solo muestra estados.
6. Estados de carga (skeleton), vacío (guía) y error (reintentar) en cada vista.
