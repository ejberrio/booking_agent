# Implementation Plan: Motor de precios

**Branch**: `003-pricing-engine` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/003-pricing-engine/spec.md`

## Summary

Capa de aplicación que expone los casos de uso de pricing sobre lo ya construido: consultar calendario (base + efectivo), asignar precio por día y por rango **con previsualización (diff) y confirmación**, gestionar promociones, y revertir cambios. Reutiliza el dominio y los servicios de la feature 001 (`pricing_service`, `audit_service`, `effective_price`, `best_promotion`, `violates_rule`) y el conector de la feature 002 para **publicar el precio efectivo** a Beds24. Añade objetos de valor de preview (transitorios), auditoría de promociones, y endpoints. Escrituras siempre con confirmación (human-in-the-loop) y reversibles.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 async, Pydantic v2; reutiliza `app/domain/pricing.py`, `app/services/pricing_service.py`, `app/services/audit_service.py` (001) y `app/services/sync_service.py` + `app/channels` (002)  
**Storage**: PostgreSQL 16 (reutiliza tablas de 001/002; añade `promotion_change_log`)  
**Testing**: pytest + pytest-asyncio; SQLite async; **ChannelManager falso** para la publicación (sin API real)  
**Target Platform**: Servidor Linux (API en `apps/api`)  
**Project Type**: Web (backend de esta feature)  
**Integration**: Publica el **precio efectivo** vía el puerto `ChannelManager` (Beds24); las promos no se mapean a las nativas de Beds24.  
**Constraints**: COP, single-tenant, solo canal Booking. Preview obligatorio en rango/bulk; detección de preview obsoleto; precios fuera de límites excluidos.  
**Scale/Scope**: 1 propiedad, horizonte ~24 meses; volumen pequeño.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| I. Spec-Driven | Procede de spec.md (003) con clarificaciones. ✅ |
| II. Provider-agnostic | Publica vía el puerto `ChannelManager`; ningún detalle de Beds24 en la capa de pricing. ✅ |
| III. Human-in-the-loop | Preview + confirmación + detección de preview obsoleto; toda escritura auditada (precio y promos) y reversible con conflicto. ✅ |
| IV. Tipado y pruebas | Servicios y objetos de valor tipados; tests del flujo (preview/apply/promos/rollback) con ChannelManager falso. ✅ |
| V. Simplicidad | Reutiliza dominio/servicios existentes; solo añade orquestación + 1 tabla de auditoría de promos. ✅ |

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-pricing-engine/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── pricing-api.md      # casos de uso/endpoints + objetos de valor + contratos de test
├── quickstart.md
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
apps/api/app/
├── schemas/                       # NUEVO: objetos de valor (Pydantic, no ORM)
│   └── pricing.py                 # RangeSelection, ChangePreview, ChangePreviewDay, ApplyResult, CalendarDayView
├── services/
│   ├── pricing_app_service.py     # NUEVO: orquestación (get_calendar, set_day, preview_range,
│   │                              #   apply_range, rollback_and_publish, publish_effective)
│   └── promotion_service.py       # NUEVO: CRUD de promociones + auditoría + recálculo/re-publicación
├── models/
│   └── audit.py                   # + PromotionChangeLog (auditoría de promos)
└── api/routes/
    └── pricing.py                 # NUEVO: GET /pricing/calendar; POST /pricing/day, /pricing/range/preview,
                                   #   /pricing/range/apply, /pricing/rollback; CRUD /pricing/promotions

apps/api/migrations/versions/      # NUEVA migración: promotion_change_log

apps/api/tests/
├── test_pricing_app.py            # get_calendar, set_day (valida+audita+publica), preview/apply rango
│                                  #   (días inválidos excluidos, preview obsoleto), rollback+publica
└── test_promotion_service.py      # CRUD + auditoría + recálculo y re-publicación del efectivo
```

**Structure Decision**: Nueva capa de aplicación (`services/pricing_app_service.py`, `services/promotion_service.py`) y objetos de valor (`schemas/pricing.py`), reutilizando el dominio/servicios de 001 y el conector de 002. La publicación pasa siempre por el puerto `ChannelManager` (inyectable → falso en tests). Se añade `PromotionChangeLog` (1 tabla) para auditar promociones.

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
