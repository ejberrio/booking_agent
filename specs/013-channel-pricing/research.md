# Research: Precios y promociones por canal

**Feature**: 013-channel-pricing · **Date**: 2026-07-02 · Fuentes: OpenAPI oficial `apiV2.yaml` (descargado) + sondas de SOLO LECTURA sobre la cuenta real.

## R1 — ¿Cómo materializar el ajuste porcentual por canal en Beds24?

- **Decision**: escribir el **multiplier del canal** vía `POST /channels/settings` (Alpha), componiendo sobre la fórmula existente: `*[CONVERT:COP-USD]` + 8% ⇒ `*[CONVERT:COP-USD]*1.08`. El dominio habla en factor decimal; el adaptador compone/parsea la fórmula.
- **Evidencia (en vivo, 2026-07-02)**:
  - `GET /channels/settings?propertyId=337229&channel[]=airbnb` → `{"multiplier": "*[CONVERT:COP-USD]", "currency": "USD", ...}` — el campo es **string** y devuelve nuestra fórmula intacta.
  - `airbnbSettingsPost.multiplier: type string, nullable` en el yaml → se puede escribir la fórmula compuesta.
  - El wiki de Beds24 documenta la composición de multiplicadores (`*1.23`, plantillas `[CONVERT:...]`).
- **Limitaciones descubiertas**:
  - El endpoint es **Alpha** → cada escritura se verifica con re-GET y fallo ⇒ SyncIssue (FR-011).
  - Canales soportados por `/channels/settings`: `airbnb`, `vrbo`, `iCal*`. **`booking` NO tiene multiplier por API** → los offsets solo son materializables para Airbnb; Booking vende al precio base (el sistema lo comunica honestamente).
- **Alternatives considered**:
  - *Slots de precio por canal (daily prices vinculados a price2..N)*: requiere reconfigurar el mapping en el dashboard, duplica la escritura de calendario y rompe la simplicidad (YAGNI) — descartado.
  - *Cambiar el multiplier a mano en el dashboard*: es lo que existe hoy; sin preview/auditoría/agente — justamente lo que la feature elimina.
  - *Aplicar el offset en la app escribiendo precios distintos*: imposible — el calendario de Beds24 es UNO para todos los canales.

## R2 — ¿Se puede limitar un fixed price (promoción) a ciertos canales?

- **Decision**: SÍ — campo `channels` del schema `fixedPrice`: objeto por canal con bandera de habilitación. Para alcance "solo Booking" se escribe `{"airbnb": {"enable": false}}` (solo los tokens gestionados que se excluyen; el resto no se toca).
- **Evidencia (en vivo)**: `GET /inventory/fixedPrices?roomId=697411` → los 6 fixed prices reales traen `channels: {"agoda": {"enable": true}, "airbnb": {"enable": true}, ...}` (todos habilitados por defecto).
- **⚠️ Discrepancia yaml vs realidad**: el yaml declara la clave **`enabled`**, el payload real usa **`enable`**. Se usa `enable` (dato real) y la prueba en vivo del quickstart lo confirma en escritura; CONFIRMADO EN ESCRITURA (T024, 2026-07-02): el POST acepta `enable` y el read-back lo refleja.
- **Campo relacionado**: `allowMultiplier` (bool) en fixedPrice — controla si el multiplier del canal aplica también al fixed price. Comportamiento deseado: dejarlo como esté (default) ⇒ una promoción en Airbnb también recibe el offset del canal (coherente con "el offset es del canal, no del precio").
- **Alternatives considered**: `channelManagement: notUsed|exportPrice|normalPrice` — es un interruptor global (canal sí/no todos), no por canal; se mantiene en su valor actual.

## R3 — ¿Qué es el "precio efectivo por canal" que se muestra?

- **Decision**: `efectivo(canal) = round(base × (1 + offset_pct/100))` en COP. La conversión `[CONVERT:COP-USD]` es **neutra en valor** (expresa el mismo importe en la moneda del listing) y no entra al cálculo mostrado; la UI lo anota ("Airbnb lo muestra en la moneda del huésped, con su margen cambiario ~8%, fuera de nuestro control").
- **Rationale**: verificado en la Fase A (issue #86): $102 ≈ 350.000 COP a tasa de mercado; el spread del ~8% lo aplica Airbnb al huésped que paga en COP y varía — no es modelable de forma estable.
- **Alternatives considered**: mostrar el precio en USD del listing (confunde: el host piensa en COP); estimar el spread de Airbnb (frágil y cambiante — descartado).

## R4 — ¿Dónde vive la UI del offset y los deep-links?

- **Decision**: offset en **Configuración** (tarjeta "Precio por canal", junto a lo demás operativo); alcance de promociones y deep-links en **Ofertas** (donde ya vive la distinción promos vs deals). Links: `https://www.airbnb.com/multicalendar` (precios/descuentos del anuncio) y Beds24 `pagetype=syncroniserairbnbpromotions`.
- **Alternatives considered**: página nueva "Canales" (fragmenta la navegación para un solo control — YAGNI).

## R5 — ¿Cómo se audita y revierte un offset?

- **Decision**: registro de auditoría por apply (origen chat/manual) con `{channel, before_pct, after_pct, before_multiplier, after_multiplier}`; revertir = nueva propuesta con `before_pct` (mismo flujo con confirmación). Patrón idéntico al de promociones (Feature 011).
- **Alternatives considered**: undo automático sin confirmación (violaría el Principio III — descartado).
