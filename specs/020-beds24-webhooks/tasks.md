# Tasks: Reservas en tiempo real (avisos de Beds24)

**Input**: Design documents from `/specs/020-beds24-webhooks/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/webhooks-api.md, quickstart.md

**Tests**: incluidos (Constitución IV: autenticación de una entrada pública y consistencia de reservas).

**Organization**: Foundational = modelo + secreto (bloquean todo). US2 (autenticación) va junto a US1 porque la ruta no puede existir sin ella.

## Format: `[ID] [P?] [Story] Description`

- **[Story]**: US1 (reservas solas), US2 (solo auténticos), US3 (robustez), US4 (estado y guía)

---

## Phase 1: Foundational (bloqueante)

- [X] T001 Modelo `apps/api/app/models/webhook.py`: enum `WebhookResult` (accepted, ignored, rejected, failed) y `WebhookEvent` (received_at tz default now, source String(20) default "beds24", result, booking_ref String(40) nullable, detail String(200) nullable, sync_run_id Integer nullable) + índice en `received_at`; exportar en `apps/api/app/models/__init__.py`
- [X] T002 Migración `apps/api/migrations/versions/a4b5c6d7e8f9_webhook_events.py` (down `f3a4b5c6d7e8`): crea el enum `webhookresult` y la tabla `webhook_event`, y un **índice único** `uq_booking_external_ref` en `booking.external_ref` (prod verificado sin duplicados el 2026-10-08; reflejarlo en `apps/api/app/models/booking.py` con `unique=True`); downgrade elimina índice, tabla y enum
- [X] T003 En `apps/api/app/services/secret_service.py`: añadir `"beds24_webhook_key"` a `SECRET_NAMES` (label "Clave de avisos de Beds24", service "Reservas en tiempo real (avisos de Beds24)", test "webhook"); `get_secret` sin fallback de entorno útil (no hay variable) → `None` = sin configurar

**Checkpoint**: 276 tests previos verdes con el modelo y la migración.

---

## Phase 2: User Story 1 + 2 — Avisos auténticos actualizan reservas (P1) 🎯 MVP

**Goal**: un aviso con clave válida re-sincroniza la reserva afectada; uno sin clave no tiene efectos.
**Independent Test**: escenarios 1–4 de quickstart.md.

- [X] T004 [US1] Crear `apps/api/app/services/webhook_service.py`: `verify_key(presented: str | None) -> Literal["ok","missing_config","invalid"]` con `hmac.compare_digest` contra `get_secret("beds24_webhook_key")`; `parse_hint(raw: bytes) -> BookingHint(booking_id, property_id, arrival, departure)` tolerante (JSON inválido o campos ausentes → valores None; nunca lanza; NO conserva el resto del cuerpo)
- [X] T005 [US1] En `webhook_service.py`: `async def handle(session, adapter, hint, *, today) -> WebhookEvent` — si `property_id` existe y no coincide con `settings.beds24_prop_id` → `ignored`; si no: rango = `[min(arrival, check_in previo de la reserva con external_ref == booking_id), max(departure, check_out previo)]` (sin fechas → hoy..hoy+90; el cron diario sigue cubriendo el año) y `sync_service.import_remote(session, adapter, desde, hasta)`; si el commit choca con el índice único (alta simultánea con el cron) → rollback y reintentar el re-sync UNA vez (el segundo intento actualiza en vez de crear); éxito → `accepted` con `sync_run_id`; excepción → rollback de lo parcial, `failed` con detail fijo `"Beds24 no respondió ({TipoDeError})"`; siempre inserta `WebhookEvent` y purga eventos > 30 días
- [X] T006 [US2] En `webhook_service.py`: `async def record_rejected(session)` (evento `rejected`, detail "clave inválida", sin contenido)
- [X] T007 [US1] Ruta `apps/api/app/api/routes/hooks.py`: `POST /hooks/beds24` lee el cuerpo crudo (`await request.body()`) y la cabecera `X-StayLever-Key`; 503 si `missing_config`; 401 + `record_rejected` si `invalid`; si `ok` → `handle` con `get_adapter()` (aclose en finally) → 200 `{"result": ...}`; commit; registrar el router en `apps/api/app/api/router.py` con prefijo `/hooks`
- [X] T008 [P] [US1] Entrada pública web `apps/web/app/api/hooks/beds24/route.ts`: solo `POST`; rechaza cuerpos > 256 KB (413); reenvía cuerpo y `X-StayLever-Key` (si viene) a `${API_INTERNAL_URL}/hooks/beds24` con `Content-Type: application/json`; devuelve status y cuerpo de la API; sin `console.log`; añadir `"/api/hooks/"` a `PUBLIC` en `apps/web/middleware.ts`
- [X] T009 [US1] Tests `apps/api/tests/test_webhooks.py` (ASGITransport + canal falso con `get_properties`/`get_rates`/`get_bookings`): sin clave configurada → 503 y sin cambios; clave ausente/incorrecta → 401, evento `rejected`, sin cambios; clave rotada (vieja → 401, nueva → 200); aviso válido de reserva nueva → la reserva aparece y la ocupación del calendario se actualiza; cancelación → estado cancelled y noches liberadas; cambio de fechas → rango re-sincronizado incluye la estancia previa; aviso de otra propiedad → `ignored` sin re-sync; ningún precio publicado al canal (el falso registra 0 escrituras); una noche bloqueada manualmente (`is_blocked`) sigue bloqueada tras el aviso; una reserva ya creada por otra vía (cron) no se duplica (índice único + reintento)

**Checkpoint**: MVP funcional por API.

---

## Phase 3: User Story 3 — Robustez (P2)

- [X] T010 [US3] Tests en `apps/api/tests/test_webhooks.py`: mismo aviso dos veces → 1 reserva; avisos en desorden (cancelación antes que nueva) → estado final = el de Beds24 (el falso devuelve el vigente); JSON inválido / sin `booking.id` → re-sync con ventana por defecto (hoy..+90); Beds24 lanza error → 200 `failed`, evento con detail fijo, sin cambios parciales; purga: evento de hace 31 días se elimina al insertar uno nuevo
- [X] T011 [US3] Test de privacidad en `apps/api/tests/test_webhooks.py`: con un cuerpo que contiene nombre de huésped y `stripeToken` centinela, ni `webhook_event` ni los logs capturados (`caplog`) contienen esos valores ni la clave

---

## Phase 4: User Story 4 — Estado y guía (P2)

- [X] T012 [US4] En `webhook_service.py`: `async def status(session, *, now) -> dict` según data-model (unconfigured/never/active/idle >7 días, last_accepted_at, counts_7d, endpoint_url = `https://staylever.com/api/hooks/beds24`, header_name) y `async def generate_key(session) -> tuple[str, str]` (`secrets.token_urlsafe(32)` → `secret_service.set_secret`) devolviendo (header_line, hint)
- [X] T013 [US4] Rutas en `apps/api/app/api/routes/hooks.py`: `GET /hooks/beds24/status` y `POST /hooks/beds24/key` (la única respuesta con el valor); en `apps/api/app/api/routes/secrets.py`, test kind `webhook` → `{"ok": configured, "detail": "último aviso: …" | "sin avisos aún" | "sin configurar"}`
- [X] T014 [US4] Tests en `apps/api/tests/test_webhooks.py`: status en cada estado; `POST /key` devuelve la línea una vez y `GET /settings/secrets` solo la pista; la clave generada autentica el siguiente aviso
- [X] T015 [P] [US4] Web: `apps/web/lib/types.ts` (`WebhookStatus`) y `apps/web/lib/api.ts` (`getWebhookStatus`, `generateWebhookKey`)
- [X] T016 [US4] Web: tarjeta "Avisos en tiempo real" en `apps/web/app/(app)/settings/page.tsx` — badge de estado (sin configurar / esperando el primer aviso / funcionando / sin actividad), último aviso y conteos 7 días; botón "Generar clave" (confirmación si ya existe: "la anterior dejará de funcionar"); muestra la línea UNA vez con botón Copiar y aviso "no se volverá a mostrar"; guía paso a paso (Beds24 → Settings → Properties → Access → Booking Webhook: Version 2, URL con botón Copiar, Custom Header = la línea, Save)

---

## Phase 5: Polish

- [X] T017 [P] `docs/operations.md`: sección "Reservas en tiempo real (Feature 020)" — configuración, estados, qué hacer si falla, rotación de la clave, privacidad
- [X] T018 Validación: `uv run ruff check . && uv run pytest -q`; `npx tsc --noEmit && npx eslint app components lib middleware.ts && npm run build`
- [ ] T019 Producción tras el deploy: aplicar migración (CD), verificar `POST /api/hooks/beds24` sin clave configurada → 503; el host genera la clave y configura Beds24 (paso manual guiado); verificar en Ajustes el primer aviso real

---

## Dependencies & Execution Order

- Phase 1 bloquea todo.
- T004–T007 en orden (mismo servicio/ruta); T008 [P] en paralelo (web); T009 tras T007.
- US3 (T010–T011) tras T009. US4: T012–T014 tras T007; T015 [P]; T016 tras T015.
- Polish al final.

## Implementation Strategy

1. MVP = Phase 1 + Phase 2 (avisos autenticados que re-sincronizan).
2. US3 endurece con tests; US4 da al host el estado, la clave y la guía (necesario para activarlo).
3. Un PR (`020-beds24-webhooks`), squash-merge, CD; activación por el host (T019).
