# Data Model: 022

Migración `c6d7e8f9a0b1` (down `b5c6d7e8f9a0`):

| Tabla | Cambio |
|---|---|
| `native_deal` | + `stacking` String(12) NOT NULL default `conditional`; `UPDATE … SET stacking='always' WHERE lower(name) LIKE '%mobile%' OR lower(name) LIKE '%móvil%'` |
| `price_suggestion` | + `applied_promotion_id` Integer NULL (promoción que aplicó la bajada) |

Sin cambios de esquema:
- `pricing_rule.min_price` (existente) = precio mínimo por noche.
- `promotion.conditions` (JSON existente) gana `source: "suggestion"` y `suggestion_ids: [..]`.

## Vista de promoción (derivada, API)
`PromotionView` + `source: "manual"|"suggestion"`, `finished: bool` (end_date < hoy), `no_free_nights: bool` (solo source=suggestion: todas sus noches futuras ocupadas).

## Preview del lote (ampliado)
Por noche: `mode: "base"|"promotion"`, `promo_price`, `promo_pct`, `clipped: bool`, `final_by_channel: {booking, airbnb}` (precio con descuentos `always`); a nivel lote: `min_price` (o null), `conditional_deals: [{channel, name, pct}]`, `overlaps: [nombre]`.
