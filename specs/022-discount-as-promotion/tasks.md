# Tasks: Bajar precios con promoción (sin tocar el precio base)

**Input**: `/specs/022-discount-as-promotion/` (plan, spec, research, data-model, contracts, quickstart)
**Tests**: incluidos (Constitución IV: dinero).

---

## Phase 1: Foundational

- [X] T001 Migración `apps/api/migrations/versions/c6d7e8f9a0b1_promo_from_suggestions.py` (down `b5c6d7e8f9a0`): `native_deal.stacking` String(12) NOT NULL server_default `conditional` + UPDATE a `always` para nombres con "mobile"/"móvil"; `price_suggestion.applied_promotion_id` Integer NULL. Modelos: `NativeDeal.stacking` en `apps/api/app/models/pricing.py`, `PriceSuggestion.applied_promotion_id` en `apps/api/app/models/market.py`
- [X] T002 [P] Dominio puro `apps/api/app/domain/promo_floor.py`: `plan_promo(base, suggested, min_price, always_pct_by_channel) -> PromoPlan(price, pct, clipped, final_by_channel, skip_reason)` (fórmula de research R4; redondeo hacia arriba a COP entero; omitir si < 1 % o mínimo ≥ base)
- [X] T003 [P] Tests `apps/api/tests/test_promo_floor.py`: sin mínimo (precio = sugerido); recorte por móvil 10 %; canal más exigente manda; omisión por mínimo ≥ base; omisión < 1 %; caso del spec (base 270.000, −15 %, mínimo 230.000, móvil 10 %)
- [X] T004 Precio mínimo: `GET/PUT /pricing/min-price` en `apps/api/app/api/routes/pricing.py` (crea/actualiza `PricingRule` de la propiedad; null = quitar; 422 si ≤ 0) + test en `apps/api/tests/test_suggestion_promotions.py`
- [X] T005 `apps/api/app/services/native_deal_service.py` + rutas de deals: aceptar/devolver `stacking`; helper `always_pct_for(session, day) -> {booking: pct, airbnb: pct}` y `conditional_deals_for(session, desde, hasta)`

**Checkpoint**: 304 tests previos verdes + dominio.

---

## Phase 2: US1 + US2 — Bajadas como promoción con piso (P1) 🎯

- [X] T006 [US1] `apps/api/app/services/suggestion_batch.py` preview: por noche válida, `mode = "promotion"` si `new_price < old_price`, si no `"base"`; para promociones aplicar `plan_promo` (piso + always por canal) → `promo_price/promo_pct/clipped/final_by_channel` u omisión (`por debajo del precio mínimo`, `menos de 1 %`); a nivel lote `min_price`, `conditional_deals`, `overlaps` (promociones activas que se solapan con los tramos); huella ampliada (modo, precio promo, recortado, solapes)
- [X] T007 [US1] `suggestion_batch.apply_batch`: tramos `base` como hoy; tramos `promotion` = noches contiguas con mismo base y mismo `promo_price` → en SAVEPOINT `offer_promotion_service.apply(price=promo_price, name="StayLever · {título} {rango}", origin=ChangeOrigin.suggestion, confirm_overlap=True)`; si `published=False`/issue o excepción → rollback + `SyncIssue` + noches `failed`; si OK → `conditions.source="suggestion"`, `conditions.suggestion_ids`, `applied_promotion_id` en las sugerencias; estado de sugerencias como en 019; resultado con `promotions`
- [X] T008 [US1] `apps/api/app/api/routes/suggestions.py`: serializar los campos nuevos del preview y del resultado
- [X] T009 [US1] Tests `apps/api/tests/test_suggestion_promotions.py`: lote mixto (subida cambia base, bajada crea promoción y NO cambia base); tramos agrupados por precio; fallo de publicación → sin promoción, failed, pendiente; recorte por mínimo y omisión; huella cambia al cambiar el mínimo o un deal → 409; promoción marcada `source=suggestion` con `suggestion_ids`; el servicio de promociones rechaza el tramo (PromotionError, p. ej. precio remoto distinto o rango pasado) → tramo `failed` sin promoción (C1); deals cuyas fechas no cubren la noche no cuentan para el piso (C2)
- [X] T010 [P] [US2] Web: tarjeta "Precio mínimo por noche" en `apps/web/app/(app)/settings/page.tsx` (ver/guardar/quitar) + `lib/api.ts` + textos es/en/pt en `lib/i18n/catalog/settings.ts`

---

## Phase 3: US3 — Transparencia en la vista previa (P2)

- [X] T011 [US3] `apps/web/components/suggestions/batch-preview-dialog.tsx`: columna de modo ("precio base" / "promoción −N %"), precio con promoción y "desde el celular" por canal (Booking / Airbnb), marca "recortado por el precio mínimo"; avisos: sin mínimo (enlace a Ajustes), descuentos condicionales, solapes; resultado con promociones creadas; tipos en `lib/types.ts`; textos en `lib/i18n/catalog/suggestions.ts` (es/en/pt); motivos nuevos en `lib/i18n/server-messages.ts`

---

## Phase 4: US4 — Ciclo de vida en Ofertas (P3)

- [X] T012 [US4] `offer_promotion_service._view` / `list_promotions`: `source`, `finished` (end_date < hoy), `no_free_nights` (source=suggestion y todas las noches futuras ocupadas); tests
- [X] T013 [US4] `apps/web/app/(app)/offers/page.tsx`: badge "desde sugerencias", estado "finalizada", aviso "sin noches libres" con acción retirar (flujo existente); selector `stacking` en deals nativos ("siempre se acumula" / "condicional"); textos es/en/pt en `lib/i18n/catalog/offers.ts`

---

## Phase 5: Polish

- [X] T014 `docs/operations.md`: sección "Bajadas como promoción (Feature 022)" (incluye: al retirar una promoción de sugerencias, la sugerencia queda "aplicada" y la retirada consta en el historial de la promoción — C3)
- [X] T015 Validación: ruff + pytest; tsc + eslint + build; demo local en es/en (lote mixto, recorte, Ofertas)
- [X] T016 Producción: migración aplicada; el host define el precio mínimo; verificación de solo lectura

## Dependencies
Phase 1 → Phase 2 (T006 → T007 → T008 → T009). T010 [P] tras T004. T011 tras T008. T012–T013 tras T001. Polish al final.
