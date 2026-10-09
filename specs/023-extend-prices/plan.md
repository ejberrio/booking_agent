# Implementation Plan: Extender precios hacia el futuro

**Branch**: `023-extend-prices` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-extend-prices/spec.md` · issue #126

## Summary

Nueva acción **"Extender precios"**. La vista previa lee el calendario real del Channel Manager entre hoy y la fecha final (por defecto hoy + 18 meses) y clasifica cada noche: ya tiene precio (no se toca), reservada (se omite), bloqueada por el host (solo precio) o sin precio y cerrada (precio y se abre). Un **dominio puro** propone una plantilla por año-mes (mediana del mismo mes conocido sin eventos, si no la mediana global, redondeada a miles), aplica el % de fin de semana y ajusta al [mínimo, máximo] de la regla. El host edita la plantilla, la vista previa se recalcula y la confirmación exige la huella. La aplicación va **por mes y en SAVEPOINT**: escribe los precios en la app (auditoría con origen `extension`), registra las aperturas de disponibilidad y publica en **una sola escritura por mes** (precio y disponibilidad juntos) con un método nuevo del puerto. Si un mes falla, se deshace en la app y queda una incidencia. Además: aviso de horizonte < 12 meses en el panel y el calendario, y corrección del "precio 0".

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: existentes; SIN dependencias nuevas
**Storage**: PostgreSQL / SQLite tests. **Una migración** (`d7e8f9a0b1c2`, down `c6d7e8f9a0b1`): valor `extension` en el enum `changeorigin` (`ALTER TYPE … ADD VALUE IF NOT EXISTS`, solo PostgreSQL) y `DELETE FROM rate WHERE base_price <= 0` (filas basura de noches sin precio).
**Testing**: pytest con canal falso (calendario remoto configurable, escritura OK/falla/no verificada); dominio puro; web tsc/eslint/build + demo local
**Target Platform**: Railway
**Project Type**: monorepo web application
**Constraints**: Principio III (vista previa + huella + confirmación reforzada); nunca tocar noches con precio, reservadas ni pasadas; nunca abrir noches bloqueadas por el host; es/en/pt; no romper 320 tests
**Scale/Scope**: ~600 noches como máximo; ~15 meses → ~30 llamadas a Beds24 (1 POST + 1 GET por mes)

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; 3 decisiones del host registradas |
| II. Provider-agnostic | ✅ método nuevo del puerto `set_calendar_entries` (lista de tramos precio/disponibilidad); el formato de Beds24 vive solo en el adaptador |
| III. Human-in-the-loop | ✅ vista previa con huella (incluye el estado remoto leído), confirmación reforzada, sin escritura automática |
| IV. Tipado y pruebas | ✅ plantilla y ajuste a límites = dinero → dominio puro con tests; servicio con canal falso (fallo por mes, obsoleta, clasificación) |
| V. Simplicidad | ✅ sin tablas nuevas; reutiliza Rate/PriceChangeLog/CalendarDay/AvailabilityChangeLog/SyncIssue |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

```text
specs/023-extend-prices/ (spec, plan, research, data-model, quickstart, contracts/extension-api.md, tasks)

apps/api/
├── app/domain/price_extension.py                # NUEVO, PURO: plantilla propuesta, precio por noche, límites
├── app/services/price_extension_service.py      # NUEVO: status, preview (lee CM), apply por mes en SAVEPOINT
├── app/channels/base.py                         # CalendarEntry + set_calendar_entries en el puerto
├── app/channels/beds24_v2.py                    # set_calendar_entries: 1 POST + 1 GET de verificación
├── app/channels/beds24.py                       # V1: ChannelError (requiere V2)
├── app/models/enums.py                          # ChangeOrigin.extension
├── migrations/versions/d7e8f9a0b1c2_price_extension.py
├── app/services/pricing_service.py              # get_price: ≤ 0 → None
├── app/services/pricing_app_service.py          # calendario/KPIs: ≤ 0 = sin precio
├── app/services/sync_service.py                 # import: no crea Rate ≤ 0; local ≤ 0 se trata como ausente
├── app/api/routes/pricing.py                    # GET /pricing/extension/status, POST …/preview, …/apply
└── tests/test_price_extension_domain.py · test_price_extension.py

apps/web/
├── components/calendar/extend-prices-dialog.tsx # NUEVO: plantilla editable, vista previa por mes, confirmación reforzada, resultado
├── components/calendar/horizon-banner.tsx       # NUEVO: aviso < 12 meses (panel y calendario)
├── app/(app)/calendar/page.tsx                  # botón "Extender precios", ?extend=1 abre el diálogo
├── app/(app)/page.tsx                           # aviso en el panel
├── lib/{types,api}.ts · lib/i18n/catalog/{calendar,dashboard}.ts
docs/operations.md                               # sección Feature 023
```

## Decisiones clave (detalle en research.md)

1. **Fuente de verdad = calendario remoto** en la vista previa (una lectura): la app solo sincroniza 365 días y el estado real de precio/apertura vive en el CM.
2. **Plantilla por año-mes**, propuesta con la mediana del mismo mes del año (sin noches con evento), si no la mediana global, redondeada a 1.000 COP.
3. **Precio por noche** = redondeo a 1.000 de plantilla × (1 + % fin de semana si es viernes o sábado), ajustado a [mínimo, máximo].
4. **Una escritura por mes** con varios tramos `{from, to, price1, numAvail?}` y una sola relectura de verificación.
5. **Huella** = parámetros + estado leído por noche objetivo (precio remoto, disponibilidad, bloqueo local, reserva).
6. **Precio 0 = sin precio** en toda la app; la migración borra las filas basura.

## Complexity Tracking

Sin violaciones.
