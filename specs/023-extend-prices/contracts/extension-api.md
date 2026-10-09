# Contract: 023

## GET /pricing/extension/status?unit_type_id=1
`{"first_unpriced_night": "2027-02-13" | null, "months_covered": 4, "needs_extension": true, "default_until": "2028-04-08", "max_until": "2028-10-08"}`

## POST /pricing/extension/preview
Body: `{"unit_type_id": 1, "until": "2028-04-08"?, "weekend_pct": 0?, "open_closed": true?, "months": [{"month": "2027-02", "price": 378000, "included": true}]?}`
- Sin `months` → plantilla propuesta. Con `months` → se usan sus precios e inclusión (los meses no enviados usan la propuesta).
- 200: `{"until", "first_target", "min_price", "max_price", "weekend_pct", "open_closed", "months": [{"month", "proposed_price", "price", "included", "nights", "weekend_nights", "weekday_price", "weekend_price", "to_open", "kept_closed", "clipped_min", "clipped_max"}], "total_nights", "total_to_open", "fingerprint"}`
- 422: `until` > hoy + 24 meses o < hoy; `weekend_pct` fuera de 0..50; `price` ≤ 0; falta el precio de un mes incluido sin propuesta.
- 502: error leyendo el Channel Manager.

## POST /pricing/extension/apply
Body: el de preview + `"fingerprint"`.
- 409 si la huella no coincide (obsoleta).
- 200: `{"months": [{"month", "status": "applied"|"failed"|"skipped", "nights", "opened", "detail"}], "applied_nights", "opened_nights", "failed_months"}`
