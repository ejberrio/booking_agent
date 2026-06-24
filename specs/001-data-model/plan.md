# Implementation Plan: Modelo de datos del dominio

**Branch**: `001-data-model` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-data-model/spec.md`

## Summary

Definir y persistir el modelo de datos del dominio (single-tenant) que sostiene la gestión de precios: propiedades, canales (Booking-first, channel-aware), tipos de unidad, calendario/disponibilidad compartida, tarifas por día, promociones y reglas, reservas, eventos, sugerencias, auditoría de cambios de precio con rollback, configuración de LLM e historial de chat. Se implementa como esquema relacional en PostgreSQL mediante SQLAlchemy 2.0 (async) y migraciones Alembic, dentro de `apps/api`. El precio efectivo se deriva (no se persiste); los cambios de precio base se registran en una bitácora append-only que habilita el rollback.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: SQLAlchemy 2.0 (async, typed `Mapped`), Alembic, Pydantic v2 (esquemas), asyncpg (driver)  
**Storage**: PostgreSQL 16  
**Testing**: pytest (+ pytest-asyncio); base de datos de prueba (transacción por test / SQLite no, Postgres real vía docker compose)  
**Target Platform**: Servidor Linux (API en `apps/api`)  
**Project Type**: Web (monorepo: backend `apps/api` + frontend `apps/web`); esta feature es backend/datos  
**Performance Goals**: Herramienta personal (1 host, pocas propiedades). Sin metas de alto rendimiento; consultas de calendario por rango de fechas deben ser instantáneas a escala de meses.  
**Constraints**: Montos en COP sin errores de redondeo (Decimal, no float). Disponibilidad compartida entre canales (no duplicada por canal). Auditoría append-only. Sin multi-tenancy.  
**Scale/Scope**: ~1–10 propiedades, pocos tipos de unidad, horizonte de calendario de ~24 meses. Volumen pequeño.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento en esta feature |
|-----------|------------------------------|
| I. Spec-Driven | Esta feature procede de `spec.md` con clarificaciones registradas. ✅ |
| II. Integraciones provider-agnostic | El modelo usa una entidad `Channel` genérica; ningún campo propietario de Beds24/Booking en el dominio (los IDs externos se aíslan en un campo opaco). ✅ |
| III. Human-in-the-loop (auditoría + rollback) | `PriceChangeLog` append-only con valor antes/después y origen; rollback como nuevo cambio auditado con detección de conflicto. ✅ |
| IV. Tipado y pruebas en los límites | Modelos SQLAlchemy tipados (`Mapped`); tests para precio efectivo, promos solapadas, auditoría y rollback. ✅ |
| V. Simplicidad (single-tenant, YAGNI) | Sin multi-tenancy; offsets por canal, promos de Airbnb y paridad avanzada quedan como espacio reservado, no implementados. ✅ |

**Resultado**: PASS (sin violaciones; sin entradas en Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/001-data-model/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones técnicas
├── data-model.md        # Fase 1: entidades, campos, relaciones, índices
├── quickstart.md        # Fase 1: cómo aplicar y verificar el modelo
├── contracts/
│   └── data-access.md   # Fase 1: contrato interno de persistencia (invariantes)
└── tasks.md             # Fase 2: /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/
├── app/
│   ├── db/
│   │   ├── base.py            # DeclarativeBase (existente)
│   │   └── session.py         # engine/session async (existente)
│   ├── models/                # NUEVO: modelos ORM por agregado
│   │   ├── __init__.py        # importa todos los modelos (autogenerate Alembic)
│   │   ├── property.py        # Property, Channel, UnitType
│   │   ├── calendar.py        # CalendarDay, Rate (precio base por unidad/día)
│   │   ├── pricing.py         # PricingRule, Promotion
│   │   ├── booking.py         # Booking (reservas/ocupación)
│   │   ├── market.py          # Event, PriceSuggestion
│   │   ├── audit.py           # PriceChangeLog
│   │   └── agent.py           # LLMConfig, Conversation, Message
│   └── domain/                # NUEVO: lógica pura (sin I/O)
│       └── pricing.py         # precio efectivo, resolución de promos, validación de reglas
├── migrations/
│   └── versions/              # NUEVA migración inicial (autogenerate)
└── tests/
    ├── test_models.py         # creación/relaciones básicas
    ├── test_pricing.py        # precio efectivo + promos solapadas + límites
    └── test_audit.py          # registro de cambios + rollback + conflicto
```

**Structure Decision**: Monorepo web ya existente. Esta feature añade `app/models/` (ORM por agregado), `app/domain/pricing.py` (lógica pura y testeable sin DB) y una migración Alembic inicial, más tests. No toca `apps/web` (el consumo desde UI/API es de features posteriores).

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
