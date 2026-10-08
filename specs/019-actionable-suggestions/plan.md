# Implementation Plan: Sugerencias accionables

**Branch**: `019-actionable-suggestions` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-actionable-suggestions/spec.md` (decisiones del host 2026-10-08)

## Summary

La pestaña Sugerencias pasa de "una tarjeta por sugerencia de un día" a **bloques vendibles con aplicación en lote**. Tres piezas en la API, todas de lectura salvo el apply:

1. **Noches vendibles** (US1): un servicio puro-sobre-BD calcula, al consultar, qué noches de cada sugerencia pendiente siguen vendibles (futuras, sin reserva confirmada, sin bloqueo). Nada se almacena: una cancelación sincronizada hace reaparecer la sugerencia en la siguiente consulta.
2. **Bloques** (US3): una función PURA agrupa las sugerencias vendibles por evento (nombre del factor `event`) o por periodo (días contiguos con la misma razón principal `gap`/`occupancy`). Nuevo `GET /suggestions/blocks`.
3. **Lote con vista previa única** (US2): `POST /suggestions/batch/preview` devuelve noche a noche (antes → después, omisiones con motivo) + huella; `POST /suggestions/batch/apply` re-calcula, compara la huella (stale → 409) y aplica **por tramos contiguos de igual precio dentro de un SAVEPOINT**: si la publicación de un tramo falla, ese tramo se revierte localmente (no queda precio local distinto del canal) y sus sugerencias siguen pendientes.

Además (US4) el motor refresca `rationale`/`confidence` de la equivalente pendiente que conserva. La web reemplaza la lista de tarjetas por bloques con casillas, barra de selección y diálogo de vista previa. El calendario y el apply individual (014) no cambian.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: existentes (FastAPI, SQLAlchemy async, TanStack Query); SIN dependencias nuevas
**Storage**: PostgreSQL (prod) / SQLite (tests). **Sin migraciones**: todo es derivado (noches vendibles, bloques) o usa columnas existentes (`rationale`, `confidence`, `status`, `applied_change_id`)
**Testing**: pytest con canal falso (`FakeCM` existente) para preview/apply/fallos de publicación; función de bloques pura con tests de dominio; web `npm run build`
**Target Platform**: Railway (api + web); el scan (cron) solo cambia en el refresco del racional
**Project Type**: monorepo web application
**Performance Goals**: listar/agrupar ~30–60 sugerencias y previsualizar ~60 noches en < 1 s percibido (consultas por rango, no por noche)
**Constraints**: Principio III (una vista previa + una confirmación, huella anti-stale); piso/techo de la regla; nunca marcar aplicada una sugerencia cuyas noches no llegaron al canal; no romper 256 tests; el flujo individual 014 intacto
**Scale/Scope**: single-tenant; ~5 archivos API + ~5 web, sin migración

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; decisiones del host registradas en la spec; sin ADR nuevo (no hay decisión de arquitectura: reutiliza preview→fingerprint→apply) |
| II. Provider-agnostic | ✅ la publicación sigue por `publish_effective` → `sync_service.publish_price` (puerto ChannelManager); nada específico de Beds24 |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ el lote exige vista previa + huella + confirmación explícita; huella distinta → 409 sin escribir; el motor solo propone |
| IV. Tipado y pruebas | ✅ es lógica que mueve dinero en lote → tests de: noches vendibles, bloques, huella stale, omisiones, fallo parcial de publicación con reversión del tramo, estado de sugerencias |
| V. Simplicidad | ✅ sin tablas ni colas nuevas; bloques y vendibles derivados al consultar; sin "editar precio", "rechazar en bloque" ni "aplicar todo" (fuera de alcance del host) |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/019-actionable-suggestions/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/suggestions-batch-api.md
└── checklists/requirements.md
```

### Source Code

```text
apps/api/
├── app/domain/suggestion_blocks.py        # NUEVO, PURO: agrupación en bloques (evento / periodo)
├── app/services/suggestion_batch.py       # NUEVO: noches vendibles, listado de bloques, preview y apply en lote
├── app/api/routes/suggestions.py          # + GET /suggestions/blocks, POST /suggestions/batch/{preview,apply}
├── app/services/suggestion_engine.py      # US4: refresca rationale/confidence de la equivalente pendiente
└── tests/test_suggestion_blocks.py · test_suggestion_batch.py · (+ caso en test_suggestion_engine.py)

apps/web/
├── app/(app)/suggestions/page.tsx         # bloques + selección + barra de acción + diálogo de vista previa
├── components/suggestions/suggestion-block.tsx      # NUEVO: bloque con casilla, noches y variación
├── components/suggestions/batch-preview-dialog.tsx  # NUEVO: vista previa única + confirmar + resultado por noche
└── lib/{types,api}.ts                     # tipos y llamadas nuevas

docs/operations.md                         # sección "Sugerencias en lote"
```

**Structure Decision**: misma estructura del monorepo. La agrupación vive en `app/domain/` (pura, testeable sin BD) y la orquestación en un servicio nuevo para no engordar `intelligence_service`.

## Decisiones clave (detalle en research.md)

1. **Vendible = futura ∧ sin reserva confirmada ∧ sin bloqueo**: reservas desde `booking` (check_in ≤ d < check_out, `confirmed`) y bloqueo desde `calendar_day.is_blocked`; además `units_available == 0` sin bloqueo cuenta como ocupada (respaldo cuando la reserva no está en la BD). Consultas por rango (una para reservas, una para calendario).
2. **Bloques puros**: entrada = sugerencias vendibles (id, noches, precio, factores); clave = `event:<nombre>` si hay factor evento, si no `period:<kind>` y se corta al haber un hueco de días. Título "Evento · 14–16 nov" o "Libre próximo · 20–22 oct" / "Ocupación alta · …".
3. **Huella del lote**: sha256 de la lista ordenada `(fecha, sugerencia_id, precio_actual, precio_nuevo, válida)` más los ids seleccionados → cualquier cambio de precio, ocupación, límites o estado de una sugerencia invalida la confirmación (409 "La vista previa cambió; revísala de nuevo").
4. **Apply por tramos con SAVEPOINT**: tramos = días contiguos con igual precio nuevo; por tramo: `begin_nested()` → `set_base_price` (origin=suggestion) → `publish_effective`; si hay incidencias → rollback del savepoint (precio local intacto) + `SyncIssue` fuera del savepoint. Resultado por noche: `applied | skipped(motivo) | failed`.
5. **Estado de las sugerencias tras el lote**: `applied` si ≥1 noche aplicada y 0 fallidas (con `applied_change_id` = primer cambio); si alguna noche falló → sigue `proposed`; si todas sus noches se omitieron → sin cambio. Nunca `applied` con noches sin publicar (SC-004).
6. **US4**: `_exists_equivalent` devuelve la sugerencia; si está `proposed/approved` se copian `rationale` y `confidence` del cálculo actual (resueltas intactas).

## Complexity Tracking

Sin violaciones que justificar.
