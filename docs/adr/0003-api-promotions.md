# ADR 0003: Gestión de promociones de precio vía API (Beds24 V2 fixed prices)

**Fecha**: 2026-07-01 · **Estado**: Aceptada · **Feature**: 011-api-promotions

## Contexto

En la Feature 009 concluimos que la API de Beds24 **no** permitía gestionar
ofertas/promociones y lo resolvimos con deep-links al panel. Al revisar de nuevo
el OpenAPI oficial (`apiV2.yaml`) y probar en vivo con nuestro token (2026-07-01),
esa conclusión resultó **incompleta**: la API V2 **sí** escribe promociones.

## Hallazgo verificado

- `POST /inventory/fixedPrices` — "Create or modify fixed prices" (crear = sin `id`;
  máx. 100 por habitación). El objeto `fixedPrice` acepta `offerId` (oferta 1–16),
  `firstNight`/`lastNight`, `roomPrice`/`roomPriceEnable`, `minNights`, `strategy`, etc.
- `GET /inventory/fixedPrices` y `GET /inventory/rooms/offers` (lectura) → 200 con
  nuestro token.
- **No hay DELETE** de fixed prices.
- El **contenedor de oferta** (`/inventory/rooms/offers`) es **solo lectura** (sin POST):
  el slot se crea una vez en el panel.
- La API V1 sigue **muerta para escrituras**.

## Decisión

1. Gestionar promociones de precio (precio con descuento sobre un rango, con estancia
   mínima opcional) desde la app, publicándolas como **fixed price** sobre una
   **oferta designada** por config (`beds24_promo_offer_id`).
2. **Retirada sin DELETE**: neutralizar (`roomPriceEnable=false`) + marcar inactiva
   y ocultar. Reversible; puede dejar un registro neutralizado hasta limpieza manual.
3. **Descuento**: aceptar % o precio; se calcula y envía **precio absoluto** (no hay
   campo de %), y se **guarda también el %** para mostrar el ahorro. El precio queda
   fijado al crear (no se recalcula si cambia el base).
4. **Reutilizar** el modelo `Promotion` existente (extendido con `unit_type_id`,
   `offer_id`, `external_id`; base/price/min_nights en `conditions`) en lugar de crear
   un modelo paralelo. El flujo por oferta vive en `offer_promotion_service`; el
   `promotion_service` clásico (recorte del precio base) se conserva sin cambios.
5. Patrón humano-en-el-bucle (preview→apply→publish→auditar con `AgentAction`),
   resiliente vía `SyncIssue`. Por chat (`propose_offer_promotion`,
   `propose_retire_offer_promotion`, `get_offer_promotions`) y por la sección "Ofertas".

## Consecuencias

- Se corrige/reabre la Feature 009: las promociones de precio ya no son solo
  deep-links; se gestionan por API.
- **Precondición**: el host crea/designa una oferta pública (`enable=always`) en el
  panel una sola vez.
- **Salvedad (fuera de alcance v1)**: que un fixed price/oferta aparezca como
  **promoción NATIVA** de Booking.com (Genius/Deals con badge) depende del mapeo de
  tarifas del canal; la API gestiona la tarifa lado Beds24. Se documenta, no se garantiza.
- La verificación de escritura real se hace de forma acotada y reversible, con
  confirmación del host (no hay DELETE en la API).
