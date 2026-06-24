# ADR-0001: Arquitectura base y stack

- **Estado:** Aceptado
- **Fecha:** 2026-06-24

## Contexto
Necesitamos una plataforma para gestionar precios/promociones de Booking.com con un agente de IA (chat), sugerencias por eventos/mercado y LLM intercambiable. Es una herramienta personal (un host) en su primera etapa.

## Decisiones

1. **Integración con Booking.com vía Channel Manager.**
   Booking.com no expone su Connectivity API a hosts individuales (solo a partners aprobados). Integraremos con un Channel Manager que ya sincroniza con Booking (candidatos: Beds24, Hostaway, Smoobu, Lobby PMS), detrás de un **adaptador provider-agnostic**. La elección concreta se hace en el spike de la Fase 2 (issue #8).

2. **Stack: Next.js + FastAPI + PostgreSQL.**
   Web en Next.js/TypeScript/Tailwind/shadcn (buen UX, ecosistema maduro). API en FastAPI/Python (idóneo para orquestación de LLM y datos). Postgres como base relacional para tarifas, reglas, reservas y auditoría.

3. **LLM multi-proveedor con LiteLLM.**
   Una capa única (`app/llm`) permite cambiar de modelo/proveedor por configuración (costo de tokens vs. capacidades). Claude por defecto.

4. **Single-tenant (YAGNI).**
   Sin multi-tenancy ni auth compleja al inicio. Se evolucionará a SaaS solo si el producto lo justifica.

5. **Human-in-the-loop.**
   El agente propone; el host confirma. Toda escritura de precios queda auditada y es reversible.

## Consecuencias
- Dependemos del Channel Manager elegido para escribir en Booking; el adaptador limita el costo de cambiarlo.
- Dos ecosistemas (JS + Python) en el monorepo: se orquestan con `Makefile` y `docker-compose`, sin gestor de monorepo JS por ahora.
- La capa LLM añade una indirección mínima a cambio de flexibilidad de proveedor.

## Alternativas descartadas
- **Connectivity Partner directo con Booking:** proceso B2B largo; queda como vía futura (issue de investigación en Fase 2).
- **Automatización del Extranet (RPA):** frágil y posible violación de ToS; solo fallback temporal.
- **Full TypeScript (Vercel AI SDK):** válido, pero Python encaja mejor para el trabajo de datos/agente del backend.
