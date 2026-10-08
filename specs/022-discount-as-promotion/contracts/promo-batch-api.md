# Contract: 022

## GET /pricing/min-price → `{"min_price": "230000.00" | null}`
## PUT /pricing/min-price `{"min_price": 230000}` | `{"min_price": null}` → mismo formato; 422 si ≤ 0.

## POST /suggestions/batch/preview (ampliado)
Items: `{date, suggestion_id, old_price, new_price, valid, reason, mode, promo_price, promo_pct, clipped, final_by_channel}`.
Raíz: `min_price`, `conditional_deals`, `overlaps`, `fingerprint` (incluye modo/precio promo/solapes).
Nuevos `reason`: `"por debajo del precio mínimo"`, `"menos de 1 %"`.

## POST /suggestions/batch/apply (ampliado)
Body igual (+ huella). Noches de promoción → `status: applied|failed`; resultado gana `promotions: [{id, name, first_night, last_night, price}]`. Huella distinta → 409.

## Native deals
`GET/POST/PATCH /pricing/native-deals` incluyen `stacking: "always"|"conditional"`.

## Promociones (lista)
`GET /pricing/promotions` items + `source`, `finished`, `no_free_nights`.
