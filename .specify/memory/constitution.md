# Booking AI Agent Constitution

## Core Principles

### I. Spec-Driven Development
Toda feature significativa nace de una especificación antes del código: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. El código implementa la spec; si la realidad obliga a desviarse, se actualiza la spec, no se improvisa en silencio. Las decisiones de arquitectura se registran como ADRs en `docs/adr/`.

### II. Integraciones provider-agnostic
El Channel Manager (Booking.com vía Beds24/Hostaway/Smoobu/Lobby) y el LLM viven detrás de adaptadores con una interfaz común. Cambiar de proveedor de Channel Manager o de modelo LLM no debe requerir reescribir la lógica de negocio. Ningún detalle propietario de un proveedor se filtra al dominio.

### III. Human-in-the-loop para escrituras (NO NEGOCIABLE)
El agente nunca cambia precios, promociones ni disponibilidad sin confirmación explícita del host (el usuario de la cuenta dueña de esos datos). Todo cambio queda en un audit log (quién, cuándo, antes/después, origen: chat/manual/sugerencia) y es reversible (undo/rollback). Las sugerencias se proponen; el host aprueba.

### IV. Tipado y pruebas en los límites
Fronteras tipadas: TypeScript en web, Pydantic/typing en API. Hay tests para lo que puede costar dinero o reputación: motor de precios, adaptadores de Channel Manager y validaciones (min/max, paridad). Lógica de pricing y adapters no se mergea sin pruebas.

### V. Simplicidad primero (YAGNI)
Preferimos lo aburrido y mantenible sobre lo ingenioso. No se añaden colas, microservicios ni abstracciones especulativas hasta que una necesidad real lo justifique. Desde la v1.1.0 la necesidad real de varios anfitriones existe (fase comercial, issue #156): el multicliente se construye lo más simple posible (una base de datos compartida con aislamiento por cuenta), sin infraestructura por cliente.

### VI. Aislamiento por cuenta (NO NEGOCIABLE)
Cada anfitrión es una **cuenta**. Todo dato del anfitrión (propiedades, calendario, reservas, sugerencias, promociones, chat, avisos, preferencias, auditoría) y toda credencial de sus canales pertenece a exactamente una cuenta, y ninguna consulta, ruta, tarea programada ni herramienta del agente puede leer o escribir datos de otra cuenta. La cuenta se deriva siempre de la sesión autenticada, nunca de un parámetro que envíe el cliente o el LLM. Los secretos de la plataforma (claves de IA, búsqueda, avisos) están separados de los de cada cuenta y solo el administrador de plataforma los ve. Toda feature que toque datos incluye pruebas de aislamiento entre dos cuentas. Los datos públicos (eventos de una ciudad, referencias de mercado de una zona) pueden compartirse entre cuentas.

## Restricciones técnicas
- Stack: Next.js + TypeScript + Tailwind + shadcn/ui (web), FastAPI + Python (api), PostgreSQL (datos).
- LLM multi-proveedor vía LiteLLM; Claude por defecto, configurable por UI (modelo, keys, presupuesto de tokens).
- Secretos cifrados en reposo; nunca credenciales en el repositorio ni en logs.
- Búsqueda web (eventos/mercado) detrás de una interfaz; proveedor configurable (Tavily/Brave/Serper).

## Flujo de desarrollo
- Trabajo planificado en GitHub Project #1 (milestones = Fases 1–7 y Comercial F0–F2).
- Cambios vía Pull Request con CI verde (lint + tests).
- Una feature de spec-kit por rama; la spec y el plan acompañan al código.

## Governance
Esta constitución guía las decisiones del proyecto. Las enmiendas se documentan en el control de versiones con su justificación. Ante conflicto entre conveniencia y estos principios, prevalecen los principios (sobre todo III).

**Version**: 1.1.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-10-10

_Enmienda 1.1.0 (2026-10-10): el principio V deja de exigir single-tenant porque la fase comercial (#156) lo justifica; se añade el principio VI (aislamiento por cuenta, no negociable)._
