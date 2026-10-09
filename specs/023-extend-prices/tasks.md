# Tasks: Extender precios hacia el futuro

**Input**: `/specs/023-extend-prices/` (plan, spec, research, data-model, contracts, quickstart)
**Tests**: incluidos (Constitución IV: dinero y escrituras al canal).

---

## Phase 1: Foundational

- [X] T001 Migración `apps/api/migrations/versions/d7e8f9a0b1c2_price_extension.py` (down `c6d7e8f9a0b1`): en PostgreSQL `ALTER TYPE changeorigin ADD VALUE IF NOT EXISTS 'extension'`; `DELETE FROM rate WHERE base_price <= 0`. `ChangeOrigin.extension` en `apps/api/app/models/enums.py`
- [X] T002 Precio 0 = sin precio (US4): `pricing_service.get_price` → `None` si ≤ 0; `pricing_app_service.get_calendar`/`get_kpis` no muestran ni cuentan ≤ 0; `sync_service.import_remote` no crea `Rate` ≤ 0 y, si el local es ≤ 0 y el remoto > 0, lo fija como baseline sin incidencia; el motor de sugerencias no sugiere noches sin precio. Tests en `apps/api/tests/test_price_extension.py`
- [X] T003 Puerto: `CalendarEntry` + `set_calendar_entries` en `apps/api/app/channels/base.py`; implementación en `apps/api/app/channels/beds24_v2.py` (un POST con todos los tramos `{from,to,price1,numAvail?}`, un GET del rango para verificar precio y disponibilidad enviada); `apps/api/app/channels/beds24.py` (V1) lanza `ChannelError`; test del cuerpo y la verificación con transporte falso en `apps/api/tests/test_price_extension.py`
- [X] T004 [P] Dominio puro `apps/api/app/domain/price_extension.py`: `round_1000`, `propose_template(known: dict[date, Decimal], event_days: set[date], months: list[str], fallback: Decimal | None) -> dict[str, Decimal | None]`, `night_price(template, day, weekend_pct, min_price, max_price) -> (price, clipped)`
- [X] T005 [P] Tests `apps/api/tests/test_price_extension_domain.py`: mediana del mismo mes sin eventos; mes sin datos → mediana global; sin datos → fallback; redondeo; viernes/sábado con %; ajuste a mínimo y máximo; feb 2027 y feb 2028 como meses distintos

**Checkpoint**: 320 tests previos verdes + dominio.

---

## Phase 2: US1 + US2 — Extender con vista previa y límites (P1) 🎯

- [X] T006 [US1] `apps/api/app/services/price_extension_service.py` `preview(session, channel, params, today)`: validar parámetros (until ∈ [hoy, hoy+24 meses], weekend_pct 0..50, precios > 0); leer el calendario remoto hoy..until; clasificar noches (con precio → fuera; reservada → fuera; bloqueada local → `kept_closed`; numAvail 0 y `open_closed` → `open`); plantilla propuesta (T004) con precios conocidos locales > 0 y días de evento; aplicar overrides e inclusión por mes; límites de `PricingRule`; agregados por mes y huella (R8)
- [X] T007 [US1] `price_extension_service.apply(session, channel, params, fingerprint, today)`: recalcular el preview → `stale` si cambia; por mes incluido, en `session.begin_nested()`: `set_base_price(origin=extension, validate_rule=False)`, `CalendarDay` + `AvailabilityChangeLog(origin=extension)` para aperturas, `channel.set_calendar_entries` con tramos contiguos de igual (precio, abrir); excepción o no verificado → rollback del mes, `SyncIssue(entity_ref="price-extension:YYYY-MM")` y mes `failed`; resultado por mes
- [X] T008 [US1] Rutas en `apps/api/app/api/routes/pricing.py`: `POST /pricing/extension/preview` (422 por validación, 502 por `ChannelError`) y `POST /pricing/extension/apply` (409 obsoleta) según `contracts/extension-api.md`
- [X] T009 [US1] Tests en `apps/api/tests/test_price_extension.py` con canal falso: clasificación (con precio intacto, reservada omitida, bloqueada solo precio, cerrada abierta); exclusión de mes; override de precio; ajuste al mínimo (US2); 422 por precio ≤ 0 y horizonte > 24 meses; huella distinta → 409 sin escrituras; aplicación crea Rate + auditoría `extension` + aperturas; fallo de un mes → sin cambios locales en ese mes, incidencia y los demás aplicados; un solo `set_calendar_entries` por mes con tramos agrupados
- [X] T010 [US1] Web: `apps/web/components/calendar/extend-prices-dialog.tsx` (fecha final, % fin de semana, abrir noches cerradas, tabla por mes con precio editable e inclusión, recalcular, avisos de ajustado, confirmación reforzada "Entiendo que se publicarán N noches…", resultado por mes); botón "Extender precios" en `apps/web/app/(app)/calendar/page.tsx` (`?extend=1` lo abre); `lib/types.ts`, `lib/api.ts`; textos es/en/pt en `lib/i18n/catalog/calendar.ts`

---

## Phase 3: US3 — Aviso de horizonte (P2)

- [X] T011 [US3] `price_extension_service.status(session, unit_type_id, today)` + `GET /pricing/extension/status` + tests (con hueco a 4 meses → needs_extension; con 13 meses → no)
- [X] T012 [US3] Web: `apps/web/components/calendar/horizon-banner.tsx` (fecha, meses, botón); en el panel `apps/web/app/(app)/page.tsx` (enlace a `/calendar?extend=1`) y en el calendario (abre el diálogo); textos es/en/pt en `lib/i18n/catalog/dashboard.ts`/`calendar.ts`

---

## Phase 4: Polish

- [X] T013 `docs/operations.md`: sección "Extender precios (Feature 023)" (hallazgo, regla, aperturas, fallo por mes, costo en Beds24)
- [X] T014 Validación: ruff + pytest; tsc + eslint + build; demo local en es/en (aviso, diálogo, ajuste, resultado)
- [ ] T015 Producción: migración aplicada; verificación de solo lectura (estado del horizonte, vista previa sin aplicar); el host confirma la extensión real desde la app; después, verificación de SC-001 (oferta de Beds24 para marzo de 2027 y de 2028 devuelve precio)

## Dependencies
T001 → T002, T007. T003 → T007. T004 → T005, T006. T006 → T007 → T008 → T009 → T010. T011 tras T006; T012 tras T010/T011. Polish al final.

## Phase 5: Addendum — aperturas no aplicadas por el CM (2026-10-09)

- [X] T016 `WriteResult.unconfirmed` (noches con disponibilidad no confirmada) en `apps/api/app/channels/base.py` y `beds24_v2.py`; `price_extension_service.apply`: relee el mes, corrige `CalendarDay`/`AvailabilityChangeLog` a lo real y devuelve `not_opened` por mes y `not_opened_nights`; tests
- [X] T017 Preview `closed_priced`/`first_closed_priced` y status `closed_nights`/`first_closed_night`; tests
- [X] T018 Web: aviso destacado en el resultado, nota en la vista previa, banner de noches cerradas, aviso en Abrir/Bloquear del calendario; textos es/en/pt
