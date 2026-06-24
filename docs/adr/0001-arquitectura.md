# ADR-0001: Arquitectura base y stack

- **Estado:** Aceptado
- **Fecha:** 2026-06-24

## Contexto
Necesitamos una plataforma para gestionar precios/promociones de Booking.com con un agente de IA (chat), sugerencias por eventos/mercado y LLM intercambiable. Es una herramienta personal (un host) en su primera etapa.

## Decisiones

1. **Integración con Booking.com vía Channel Manager → Beds24.**
   Booking.com no expone su Connectivity API a hosts individuales (solo a partners aprobados). Integraremos con un Channel Manager que ya sincroniza con Booking, detrás de un **adaptador provider-agnostic**. Elegimos **Beds24**: la API REST más potente y mejor documentada, el más económico (~€8.40/mes + €0.55/conexión, sin comisiones), preferred partner de Booking.com y precios transparentes. Su "curva de aprendizaje" se refiere a su UI propia, que no usamos (operamos por API). El spike de la Fase 2 (issue #8) valida en sandbox la escritura de tarifas por día y promociones antes de comprometer la integración. Alternativas descartadas: Smoobu (API floja para tarifas), Hostaway ($100+/propiedad, orientado a gestores grandes), Channex (más caro, orientado a white-label/PMS).

2. **Stack: Next.js + FastAPI + PostgreSQL.**
   Web en Next.js/TypeScript/Tailwind/shadcn (buen UX, ecosistema maduro). API en FastAPI/Python (idóneo para orquestación de LLM y datos). Postgres como base relacional para tarifas, reglas, reservas y auditoría.

3. **LLM multi-proveedor con LiteLLM → OpenAI (dos niveles).**
   Una capa única (`app/llm`) permite cambiar de modelo/proveedor por configuración (costo de tokens vs. capacidades). Usamos OpenAI con estrategia de dos niveles: `gpt-4o-mini` para tareas de alto volumen/bajo riesgo (leer y resumir eventos/mercado, desarrollo) y `gpt-4o` para el loop del agente que **escribe precios** (mejor tool-calling y razonamiento numérico). Cambiar de modelo es trivial gracias a LiteLLM.

4. **Búsqueda web → Tavily.**
   Para descubrir eventos en Medellín y referencias de mercado usamos Tavily: tier gratis de 1.000 créditos/mes sin tarjeta y salida optimizada para agentes (contenido limpio y resumido → menos tokens). Detrás de una interfaz para poder cambiar a Brave/Serper si el volumen lo exige.

5. **Single-tenant (YAGNI).**
   Sin multi-tenancy ni auth compleja al inicio. Se evolucionará a SaaS solo si el producto lo justifica.

6. **Human-in-the-loop.**
   El agente propone; el host confirma. Toda escritura de precios queda auditada y es reversible.

## Consecuencias
- Dependemos del Channel Manager elegido para escribir en Booking; el adaptador limita el costo de cambiarlo.
- Dos ecosistemas (JS + Python) en el monorepo: se orquestan con `Makefile` y `docker-compose`, sin gestor de monorepo JS por ahora.
- La capa LLM añade una indirección mínima a cambio de flexibilidad de proveedor.

## Alternativas descartadas
- **Connectivity Partner directo con Booking:** proceso B2B largo; queda como vía futura (issue de investigación en Fase 2).
- **Automatización del Extranet (RPA):** frágil y posible violación de ToS; solo fallback temporal.
- **Full TypeScript (Vercel AI SDK):** válido, pero Python encaja mejor para el trabajo de datos/agente del backend.
