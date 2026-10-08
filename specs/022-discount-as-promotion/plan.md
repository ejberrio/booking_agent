# Implementation Plan: Bajar precios con promoción (sin tocar el precio base)

**Branch**: `022-discount-as-promotion` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-discount-as-promotion/spec.md` · issue #128

## Summary

El lote de sugerencias (feature 019) gana un **modo por noche**: `base` (subidas, como hoy) o `promotion` (bajadas). Las bajadas se agrupan en tramos contiguos con el **mismo precio base y el mismo precio con promoción** y cada tramo se publica con el servicio de promociones por rango existente (`offer_promotion_service.apply`, feature 011: fixed price en la oferta designada, Booking.com + Airbnb), marcado como `source=suggestion` y enlazado a sus sugerencias. Un **dominio puro** calcula el precio de la promoción respetando el **precio mínimo** (reutiliza `PricingRule.min_price`, hoy sin fila) contra los **descuentos siempre acumulables** de cada canal (deals nativos con nuevo campo `stacking`). La vista previa única muestra base, %, precio con promoción y precio "desde el celular" por canal, avisa descuentos condicionales, solapes y la falta de mínimo. Ofertas distingue promociones de sugerencias y marca las finalizadas.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: existentes; SIN dependencias nuevas
**Storage**: PostgreSQL / SQLite tests. **Una migración** (`c6d7e8f9a0b1`, down `b5c6d7e8f9a0`): `native_deal.stacking` (String(12), `always`|`conditional`, default por nombre: "mobile" → always), `price_suggestion.applied_promotion_id` (int, nullable). Las promociones guardan `source`/`suggestion_ids` en su JSON `conditions` existente.
**Testing**: pytest con canal falso (publicación de fixed prices OK/falla) y dominio puro del piso; web tsc/eslint/build + revisión visual en demo local
**Target Platform**: Railway
**Project Type**: monorepo web application
**Constraints**: Principio III (una vista previa + una confirmación por lote, huella incluye modo y precio de promoción); sin promoción activa si su publicación falla; tope del motor −15 % intacto; es/en/pt; no romper 304 tests
**Scale/Scope**: ~5 archivos API + ~5 web + 1 migración

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; 3 decisiones del host registradas |
| II. Provider-agnostic | ✅ la promoción se publica por el puerto existente (`publish_promotion` → `RemoteFixedPrice`); el piso usa deals registrados, no APIs de plataformas |
| III. Human-in-the-loop | ✅ lote con huella; las promociones solo se crean tras confirmar; solapes requieren confirmación explícita |
| IV. Tipado y pruebas | ✅ el cálculo del piso es dinero → función pura con tests; lote mixto, fallo de publicación, recorte, omisión |
| V. Simplicidad | ✅ reutiliza promociones 011, PricingRule y deals 015; sin tablas nuevas |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

```text
specs/022-discount-as-promotion/ (plan, research, data-model, quickstart, contracts/promo-batch-api.md, tasks)

apps/api/
├── app/domain/promo_floor.py                 # NUEVO, PURO: precio de promoción con piso y descuentos acumulables
├── app/models/pricing.py                     # NativeDeal.stacking
├── app/models/market.py                      # PriceSuggestion.applied_promotion_id
├── migrations/versions/c6d7e8f9a0b1_promo_from_suggestions.py
├── app/services/suggestion_batch.py          # modo base/promotion en preview y apply; tramos de promoción
├── app/services/offer_promotion_service.py   # `source`/`suggestion_ids` en conditions; vista con source/finished/no_free_nights
├── app/services/native_deal_service.py       # stacking en create/update/list
├── app/api/routes/pricing.py                 # GET/PUT /pricing/min-price; deals con stacking
├── app/api/routes/suggestions.py             # serializa campos nuevos del preview/resultado
└── tests/test_promo_floor.py · test_suggestion_promotions.py

apps/web/
├── components/suggestions/batch-preview-dialog.tsx   # columnas modo/precio desde el celular, avisos
├── app/(app)/offers/page.tsx                          # badge "desde sugerencias", finalizada, sin noches libres; stacking de deals
├── app/(app)/settings/page.tsx                        # tarjeta "Precio mínimo por noche"
├── lib/{types,api}.ts · lib/i18n/catalog/{suggestions,offers,settings}.ts
```

## Decisiones clave (detalle en research.md)

1. **Precio mínimo = `PricingRule.min_price`** (una sola noción de mínimo en la app; al configurarlo también valida cambios de base, comportamiento ya existente).
2. **Piso por canal**: `precio_promo ≥ max(mínimo, máx_c mínimo / (1 − a_c))`, con `a_c` = suma de deals `always` activos del canal en esa noche (peor caso). Redondeo hacia arriba a COP entero.
3. **Una sola promoción por tramo y en ambos canales** con el precio que respeta el piso en el canal más exigente (la promoción es la misma en Booking y Airbnb).
4. **Omisiones**: bajada < 1 % tras recortar → `menos de 1 %`; mínimo ≥ base → `por debajo del precio mínimo`.
5. **Fallo de publicación**: el tramo de promoción va en SAVEPOINT; si `publish_promotion` devuelve issue o lanza → rollback (no queda promoción) + `SyncIssue`, noches `failed`, sugerencias pendientes.
6. **Ofertas**: `finished = end_date < hoy` (sin migrar estados), `source` desde `conditions`, `no_free_nights` = todas sus noches futuras ocupadas.

## Complexity Tracking

Sin violaciones.
