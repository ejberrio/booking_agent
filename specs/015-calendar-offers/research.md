# Research: Feature 015 — Calendario con ofertas + registro de deals nativos

**Date**: 2026-07-03 · Método: lectura del código (sin APIs externas nuevas — precisamente porque los deals NO tienen API, hallazgo ya verificado en 009/011/013).

## R1. ¿Dónde vive hoy la "advertencia de doble descuento"?

- **Hallazgo**: NO existe en el backend. `offer_promotion_service.preview` solo advierte de (a) solape con otras promociones de la app y (b) reservas confirmadas en el rango. La "advertencia" de doble descuento es estática: la tarjeta-guía de la sección Ofertas y una regla del prompt del agente.
- **Decision**: FR-007 se implementa como un warning NUEVO en `preview` (por cada `NativeDeal` activo que solape en fechas y canal), sin tocar los warnings existentes. No bloquea la creación (warning, no error): combinar descuentos a propósito es legítimo; el objetivo es que nunca pase por accidente.
- **Rationale**: `preview` es el único cuello por donde pasan las promos (web Y agente vía tools) → una sola implementación protege ambos caminos.
- **Alternatives considered**: bloquear con `confirm_overlap` como el solape de promos (más fricción; el doble descuento entre canal y app no siempre es error — rechazado); validar en apply (tarde: el host ya decidió — rechazado).

## R2. Fuente de datos del marcado y el detalle en el calendario

- **Decision**: merge client-side, patrón 014. Deals: nuevo `GET /pricing/native-deals`. Promos de la app: `GET /pricing/promotions` EXISTENTE ya expone `name`, `discount_pct`, `first_night`/`last_night`, `channels_scope` y `status` — todo lo que el panel del clic necesita. El endpoint `/pricing/calendar` no se toca (su campo `promotions: list[str]` sigue alimentando el punto ámbar como hoy).
- **Rationale**: SC-004 (comportamiento idéntico sin datos) por construcción; cero riesgo de regresión en el endpoint más usado; listas pequeñas (decenas) → cruce trivial en el cliente; la caché de react-query ya comparte la query de promociones con la página Ofertas.
- **Alternatives considered**: enriquecer `CalendarDayView` server-side (rompería el tipo `promotions: string[]` de la web o exigiría campo paralelo + N+1 de consultas — rechazado).

## R3. Modelo NativeDeal y semántica de rangos abiertos

- **Decision**: tabla plana `native_deal`: `channel` (enum `ChannelKind` existente; el servicio restringe a booking/airbnb), `name` (≤120, requerido), `discount_pct` (Numeric(5,2), 0–100), `date_from`/`date_to` (Date, **nullable** = extremo abierto; ambos NULL = "siempre activo"), `is_active` (bool, default true) + timestamps. Solape con `[first, last]`: `(date_from IS NULL OR date_from <= last) AND (date_to IS NULL OR date_to >= first)`. Canal ∩ scope: `scope is None` → solapa cualquier canal; si no, `deal.channel.value ∈ scope`.
- **Rationale**: los semanal/mensual de Airbnb no tienen fechas (rango abierto); el "mín 3 noches" y detalles similares caben en el nombre (assumption de la spec); ChannelKind reutilizado evita un enum nuevo en BD.
- **Alternatives considered**: campo `deal_type` estructurado (weekly/monthly/basic…) — sin consumidor real hoy, YAGNI; enum nuevo `NativeDealChannel` — duplicaría ChannelKind.
- **Migración**: `c9d0e1f2a3b4_native_deal` (down_revision `b7c8d9e0f1a2`), patrón `postgresql.ENUM(..., name='channelkind', create_type=False)` para reutilizar el enum existente (igual que channel_offset_log con changeorigin).

## R4. CRUD sin fingerprint (Principio III)

- **Decision**: `POST/PATCH/DELETE /pricing/native-deals` directos, sin preview→confirm.
- **Rationale**: el Principio III protege escrituras a los CANALES (precios/promos/disponibilidad). Un NativeDeal es una anotación local que no publica nada; exigir fingerprint sería teatro de seguridad y fricción contra el objetivo de "10 segundos". El DELETE es real (es una nota, no un registro de auditoría).
- **Alternatives considered**: soft-delete universal — la spec ya cubre el caso útil con `is_active`; borrar es para errores de captura.

## R5. UI: dónde vive cada pieza

- **Decision**: (a) Sección Ofertas: tarjeta "Deals nativos registrados" con lista (canal, nombre, %, vigencia o "siempre activo", interruptor activo) + formulario de alta + editar/borrar; la guía existente de 3 vías se enlaza con el registro ("cuando crees un deal en el panel, anótalo aquí"). (b) Calendario y dashboard: `PriceCalendar` gana `nativeDealDates?: Set<string>` → punto **cian** (`bg-cyan-500`; libres: rojo=reserva, gris=bloqueo, ámbar=promo, violeta=sugerencia) + leyenda "Deal nativo". (c) Panel "Ofertas del día" (`offers-panel.tsx`): al clic en un día con ofertas, lista promos de la app (nombre, %, alcance) y deals (nombre, canal, %, vigencia/siempre activo); convive con SuggestionPanel.
- **Rationale**: paridad con el patrón 014; el canal del deal se ve en el panel (celda demasiado pequeña para distinguir canal, assumption de la spec).

## R6. Semilla de los 3 deals reales

- **Decision**: tras el deploy, registrar por API (con confirmación del host): "Vacaciones Julio · mín 3" (booking, 20, 2026-07-03→2026-07-31), "Descuento semanal" (airbnb, 5, abierto), "Descuento mensual" (airbnb, 25, abierto).
- **Rationale**: datos del host, no del esquema — no van en la migración; el CRUD queda verificado en vivo de paso (SC-001/SC-005).
