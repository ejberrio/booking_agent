# Research: Bajar precios con promoción (022)

## R1. ¿Cómo publicar la bajada como promoción?
- **Decision**: reutilizar `offer_promotion_service.apply(price=<precio con promoción>, name=…, origin=ChangeOrigin.suggestion, confirm_overlap=<confirmado en el lote>, channels_scope=None)`.
- **Rationale**: ya publica un *fixed price* en la oferta designada de Beds24 (visible como promoción/deal en Booking.com y Airbnb), audita en `PromotionChangeLog`, sabe retirar y lista en Ofertas. Un fixed price es **un precio por rango** → los tramos deben tener mismo base y mismo precio con promoción.
- **Alternatives**: deals nativos de cada OTA (no hay API); bajar el base (rechazado por el host).

## R2. ¿Qué es el "precio mínimo"?
- **Decision**: `PricingRule.min_price` de la propiedad (crear la fila si no existe) vía `GET/PUT /pricing/min-price`.
- **Rationale**: el motor ya respeta `min_price` como piso de sugerencias y `set_base_price` lo valida; un único concepto de mínimo evita contradicciones. Hoy no hay fila → sin cambios de comportamiento hasta que el host lo defina.

## R3. ¿Qué descuentos cuentan para el piso?
- **Decision**: campo `native_deal.stacking ∈ {always, conditional}`; `always` suma para el piso (peor caso, por canal y si el deal cubre la noche); `conditional` solo se informa. Migración: nombres con "mobile"/"móvil" → `always`, resto → `conditional`; editable en Ofertas.
- **Rationale**: los descuentos por estadía larga o anticipación no aplican a todas las reservas; sumarlos haría el piso irrealmente alto. El descuento móvil sí puede aplicar a cualquier reserva.

## R4. Fórmula
`floor_c = min_price / (1 − a_c)`; `piso = max(min_price, max_c floor_c)`; `precio_promo = max(sugerido, ceil(piso))`; si `precio_promo ≥ base × 0,99` → omitir. Sin `min_price` → `precio_promo = sugerido` y aviso.

## R5. Huella del lote
- Se amplía con `modo|precio_promo|recortado` por noche y con la lista de solapes → cualquier cambio de mínimo, deals o promociones invalida la confirmación (409).
