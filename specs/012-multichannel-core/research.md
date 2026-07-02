# Research: Núcleo multi-canal

**Feature**: 012-multichannel-core · **Date**: 2026-07-02

## R1 — ¿De dónde sale el canal de origen de una reserva?

- **Decision**: usar el campo `channel` del `GET /bookings` de Beds24 V2, con fallback a `referer`.
- **Rationale**: verificado en vivo (2026-07-02) contra la cuenta real: la reserva de Booking llega con `{"referer": "Booking.com", "apiSourceId": 19, "channel": "booking"}`. `channel` ya es un token normalizado en minúsculas; `referer` es texto display. Airbnb llega análogamente con `channel: "airbnb"` (documentado por Beds24; se verifica con la primera reserva real o de prueba).
- **Alternatives considered**: `apiSourceId` (numérico, tabla propietaria sin documentación estable — descartado); inferencia por heurística de nombre del huésped (frágil — descartado).

## R2 — ¿Cómo corregir las reservas históricas mal etiquetadas?

- **Decision**: dentro del import existente: si la reserva ya existe (match por `external_ref`) y su `channel_kind` difiere del reportado, actualizarla. Sin migración Alembic, sin script one-off.
- **Rationale**: Beds24 es la fuente de verdad; el import ya des-duplica por `external_ref` (0 duplicados garantizados); re-importar es la operación de recuperación estándar del proyecto (docs/deploy.md). Un data-fix por migración duplicaría lógica y quedaría obsoleto.
- **Alternatives considered**: migración de datos Alembic (no puede saber el canal real sin llamar a la API — descartada); endpoint admin ad-hoc (superficie extra innecesaria; el import ya existe y es idempotente — descartado).

## R3 — ¿Cómo saber qué canales están "conectados"?

- **Decision**: configuración explícita `CHANNELS_ACTIVE` (CSV, default `booking,airbnb`); el import upserta los `Channel` configurados como activos y desactiva los demás.
- **Rationale**: Beds24 no expone de forma estable/consultable el estado de conexión por canal vía API (verificado: `GET /channels/airbnb` devuelve null/`Invalid data` según parámetros incluso con el canal conectado). Single-tenant: el operador SABE qué conectó (issue #86); config explícita es simple, honesta y cubre el edge case "canal desconectado" (se quita de la config → queda inactivo sin ocultar reservas históricas).
- **Alternatives considered**: detección automática vía API de Beds24 (no confiable — descartada); activar canal al observar su primera reserva (Airbnb aparecería como inactivo hasta la primera reserva, estado engañoso — descartado como criterio único; nota: el import PUEDE marcar activo un canal no configurado si llegan reservas suyas — decisión menor para implement).

## R4 — ¿Dónde inyectar los canales activos al agente?

- **Decision**: `system_prompt(today, active_channels: list[str])`; el orquestador consulta los `Channel.is_active` de la BD (consulta barata) al armar el prompt, igual que ya inyecta la fecha y las unidades.
- **Rationale**: patrón ya establecido en `orchestrator.py` (`system_prompt() + _units_context(session)`); mantiene el prompt como función pura y testeable.
- **Alternatives considered**: hardcodear "Booking y Airbnb" en el texto (volvería a mentir si cambia la config — descartado); tool `get_channels` (el agente tendría que llamarla siempre; el dato es estático por sesión — descartado).

## R5 — ¿El filtro por canal va en la tool o lo hace el LLM?

- **Decision**: parámetro opcional `channel` en la tool `get_bookings` (filtro en SQL) y campo `channel` en cada reserva devuelta.
- **Rationale**: filtrar en la fuente es determinista y barato; devolver el canal permite además la escena "todas mis reservas" con canal visible (US2-AS2). El LLM solo decide qué pedir.
- **Alternatives considered**: devolver todo y que el LLM filtre (gasta tokens y puede equivocarse — descartado).

## R6 — ¿El dashboard necesita endpoint nuevo?

- **Decision**: no; extender `GET /status` con el bloque `channels` y consumirlo vía el proxy existente (`/api/proxy/status`).
- **Rationale**: /status ya es el "estado del sistema" (patrón resiliente con checks aislados); la web ya habla con la API solo vía proxy autenticado. Un endpoint nuevo sería superficie duplicada.
- **Alternatives considered**: endpoint `/channels` dedicado (YAGNI — descartado); consulta directa de la web a la BD (viola la arquitectura — descartado).
