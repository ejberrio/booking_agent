# Research & Decisiones — Gestión de disponibilidad

Formato: Decisión / Razón / Alternativas.

## 1. Escritura de disponibilidad en Beds24 V2

- **Decisión**: `set_availability_range(room, from, to, num_avail)` → `POST /inventory/rooms/calendar` con `[{"roomId":..,"calendar":[{"from","to","numAvail":N}]}]`. Bloquear = `numAvail=0`; abrir = `numAvail=units_count` (1). Verificación por relectura (get_rates devuelve `available`).
- **Razón**: V2 ya escribe el calendario por rango (mismo endpoint que el precio). Es la API soportada.
- **Alternativas**: V1 setRoomDates (escrituras muertas) — rechazado. El adapter V1 implementa el método pero lanza `ChannelError` para cumplir el puerto.

## 2. Distinguir "bloqueo del host" de "noche reservada"

- **Decisión**: usar `CalendarDay.is_blocked`. **Bloquear** = `units_available=0` + `is_blocked=True`. **Abrir** = `units_available=units_count` + `is_blocked=False`. Una **noche reservada** (cubierta por una reserva confirmada) tiene `units_available=0` SIN `is_blocked`; esas noches **se omiten** en bloquear y en abrir (nunca se alteran).
- **Razón**: separar el cierre manual del host de la ocupación por reserva permite reabrir solo lo que el host cerró y nunca romper/oversell una reserva (FR-005, SC-002).
- **Alternativas**: inferir solo por `units_available` — ambiguo (no distingue reserva de bloqueo). Rechazado.

## 3. Detección de noche reservada

- **Decisión**: una noche está reservada si existe una `Booking` con `status=confirmed` que la cubre (`check_in <= noche < check_out`). Se consulta una vez por rango.
- **Razón**: las reservas confirmadas son la fuente de verdad de ocupación (ya importadas de Beds24).
- **Alternativas**: usar `units_available==0` como proxy — confunde bloqueo con reserva. Rechazado.

## 4. Auditoría y reversibilidad

- **Decisión**: nueva tabla `AvailabilityChangeLog` (unit_type_id, date, old_units_available, new_units_available, was_blocked, is_blocked, origin, created_at) reutilizando el enum `ChangeOrigin` (manual/chat). La **reversión es la operación inversa** (abrir deshace bloquear); NO hay rollback por id (decidido en clarify).
- **Razón**: FR-007 exige auditoría (qué/antes/después/cuándo/origen); el inverso ya cubre el "deshacer". Una migración pequeña, análoga a `PriceChangeLog`.
- **Alternativas**: reusar `PriceChangeLog` — mezcla semánticas distintas. Rechazado. No persistir auditoría — incumple FR-007. Rechazado.

## 5. Publicación resiliente

- **Decisión**: `sync_service.publish_availability` calca `publish_price`: llama al adapter; si lanza `ChannelError`, registra `SyncIssue` (comm_error) y conserva el cambio local; verifica por relectura.
- **Razón**: FR-006, coherencia con el patrón de precios.
- **Alternativas**: fallar la operación si Beds24 falla — peor UX, rechazado.

## 6. Flujo propone→confirma (chat y API)

- **Decisión**: reutilizar `AgentAction` + `Proposal`. Nuevas herramientas `propose_block_availability` / `propose_open_availability` (date_from, date_to, weekdays opcional). `build_proposal` genera un preview (noches afectadas/omitidas, aviso si es grande); `apply_proposal` aplica vía `availability_service` con `origin=chat`. Endpoints REST análogos: `POST /pricing/availability/preview` y `/apply` (con fingerprint para detección de obsolescencia), usados por el calendario.
- **Razón**: máxima reutilización del mecanismo humano-en-el-loop ya probado.
- **Alternativas**: un flujo nuevo paralelo — más código, rechazado.

## 7. Estados visuales en el calendario (US3)

- **Decisión**: cada noche muestra uno de 4 estados: **disponible** (available>0), **reservada** (available=0 y cubierta por reserva), **bloqueada** (is_blocked), **sin datos** (available=null/base=null). El editor de rango añade acciones **Bloquear** / **Abrir** con preview→confirmar.
- **Razón**: FR-010/FR-011; el host necesita ver y gestionar visualmente.
- **Nota**: el endpoint de calendario debe exponer también `is_blocked` (o un campo `state`) para que el frontend distinga bloqueada de reservada.

## 8. Reglas de aplicación (resumen)

- Bloquear un rango: para cada noche del rango (con filtro de weekdays si aplica) que NO tenga reserva confirmada → `units_available=0`, `is_blocked=True`. Noches con reserva: omitir + informar. Idempotente.
- Abrir un rango: para cada noche con `is_blocked=True` (y sin reserva) → `units_available=units_count`, `is_blocked=False`. Noches reservadas o ya disponibles: omitir/idempotente.
- Publicar a Beds24 el nuevo `numAvail` por rango; registrar incidencia si falla.
