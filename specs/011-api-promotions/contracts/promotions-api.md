# Contract: API interna de promociones

**Feature**: 011-api-promotions · Base: `/pricing/promotions` (tras el proxy autenticado de la web)

Sigue el patrón preview→apply de precios/disponibilidad (features 003/008): la propuesta se calcula y se muestra; el host confirma; se aplica y publica. Respuestas resilientes (nunca 5xx por fallo del canal salvo error interno real).

## GET /pricing/promotions

Lista las promociones (activas y retiradas) de la unidad.

- **Query**: `unit_type_id` (int, requerido)
- **200** → `{ "promotions": PromotionView[] }`

```jsonc
// PromotionView
{
  "id": 12,
  "name": "Vacaciones enero",
  "offer_id": 3,
  "first_night": "2027-01-15",
  "last_night": "2027-01-31",
  "base_price": 350000,
  "price": 280000,
  "discount_pct": 20,
  "saving": 70000,          // base_price - price
  "min_nights": 3,
  "status": "published",     // published | sync_error | retired
  "published": true
}
```

## POST /pricing/promotions/preview

Calcula y devuelve la propuesta sin aplicar nada.

- **Body**:
```jsonc
{
  "unit_type_id": 1,
  "first_night": "2027-01-15",
  "last_night": "2027-01-31",
  "name": "Vacaciones enero",
  "discount_pct": 20,        // o bien:
  "price": null,             // precio absoluto (uno de los dos: pct o price)
  "min_nights": 3            // opcional
}
```
- **200** → `PromotionPreview`:
```jsonc
{
  "offer_id": 3,
  "offer_name": "Promociones",
  "first_night": "2027-01-15",
  "last_night": "2027-01-31",
  "base_price": 350000,
  "price": 280000,
  "discount_pct": 20,
  "saving": 70000,
  "min_nights": 3,
  "warnings": ["Se solapa con 'Año nuevo' (28-31 ene)", "3 noches ya reservadas en el rango"],
  "fingerprint": "…"        // para detectar cambios entre preview y apply (patrón existente)
}
```
- **400** (validación): precio ≤ 0, precio ≥ base, pct fuera de (0,100), rango inválido/pasado, oferta designada inexistente → `{ "detail": "<mensaje claro>" }`

## POST /pricing/promotions/apply

Crea (o edita, si `id` presente) la promoción y la publica en el canal.

- **Body**: `PromotionPreview` confirmado + `fingerprint` + `id?` (para edición) + `confirm_overlap?: bool`
- **200** → `PromotionApplyResult`:
```jsonc
{ "id": 12, "status": "published", "external_id": 55123, "published": true, "issue": null }
```
- **409**: `fingerprint` obsoleto (el base/estado cambió desde el preview) → re-preview.
- **200 con `status: "sync_error"`**: se guardó la promo pero falló la publicación; `issue` describe la incidencia (no rompe).

## POST /pricing/promotions/retire

Retira (neutraliza + oculta) una promoción publicada.

- **Body**: `{ "id": 12, "confirm": true }`
- **200** → `{ "id": 12, "status": "retired" }`
- **200 con `status: "sync_error"`**: falló neutralizar en el canal; incidencia registrada; sigue visible como no retirada del todo.

## Notas

- El `offer_id` sale de config (`beds24_promo_offer_id`); el endpoint no lo recibe del cliente.
- La preview usa el precio base del calendario (adapter `get_rates`) para `base_price`/`saving`.
- Auditoría (`AgentAction`) e incidencias (`SyncIssue`) se registran en apply/retire.
