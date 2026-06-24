# Booking AI Agent Constitution

## Core Principles

### I. Spec-Driven Development
Toda feature significativa nace de una especificación antes del código: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. El código implementa la spec; si la realidad obliga a desviarse, se actualiza la spec, no se improvisa en silencio. Las decisiones de arquitectura se registran como ADRs en `docs/adr/`.

### II. Integraciones provider-agnostic
El Channel Manager (Booking.com vía Beds24/Hostaway/Smoobu/Lobby) y el LLM viven detrás de adaptadores con una interfaz común. Cambiar de proveedor de Channel Manager o de modelo LLM no debe requerir reescribir la lógica de negocio. Ningún detalle propietario de un proveedor se filtra al dominio.

### III. Human-in-the-loop para escrituras (NO NEGOCIABLE)
El agente nunca cambia precios, promociones ni disponibilidad sin confirmación explícita del host. Todo cambio queda en un audit log (quién, cuándo, antes/después, origen: chat/manual/sugerencia) y es reversible (undo/rollback). Las sugerencias se proponen; el host aprueba.

### IV. Tipado y pruebas en los límites
Fronteras tipadas: TypeScript en web, Pydantic/typing en API. Hay tests para lo que puede costar dinero o reputación: motor de precios, adaptadores de Channel Manager y validaciones (min/max, paridad). Lógica de pricing y adapters no se mergea sin pruebas.

### V. Simplicidad primero (single-tenant, YAGNI)
Arrancamos single-tenant (herramienta personal). No se añade multi-tenancy, colas, microservicios ni abstracciones especulativas hasta que una necesidad real lo justifique. Preferimos lo aburrido y mantenible sobre lo ingenioso.

## Restricciones técnicas
- Stack: Next.js + TypeScript + Tailwind + shadcn/ui (web), FastAPI + Python (api), PostgreSQL (datos).
- LLM multi-proveedor vía LiteLLM; Claude por defecto, configurable por UI (modelo, keys, presupuesto de tokens).
- Secretos cifrados en reposo; nunca credenciales en el repositorio ni en logs.
- Búsqueda web (eventos/mercado) detrás de una interfaz; proveedor configurable (Tavily/Brave/Serper).

## Flujo de desarrollo
- Trabajo planificado en GitHub Project #1 (milestones = Fases 1–7).
- Cambios vía Pull Request con CI verde (lint + tests).
- Una feature de spec-kit por rama; la spec y el plan acompañan al código.

## Governance
Esta constitución guía las decisiones del proyecto. Las enmiendas se documentan en el control de versiones con su justificación. Ante conflicto entre conveniencia y estos principios, prevalecen los principios (sobre todo III).

**Version**: 1.0.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
