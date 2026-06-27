# ADR 0002: Despliegue en Railway + Neon, con API privada tras un proxy

- **Estado**: Aceptado
- **Fecha**: 2026-06-26
- **Feature**: 007-production-deploy

## Contexto

Booking_AI_Agent debe pasar de "corre en local" a una URL pública, segura y estable, para un único host (single-tenant), con presupuesto bajo. La web (Next.js) llama hoy a la API (FastAPI) **directamente desde el navegador** y la **API no tiene autenticación propia** (solo la web está protegida por contraseña). Exponer la API públicamente permitiría a cualquiera cambiar precios reales en Booking.

## Decisión

1. **Hosting**: web + API en **Railway** (plan Hobby, por uso); **Postgres gestionado en Neon** (tier gratis).
2. **Topología segura**: la **web es el único servicio público**; la **API vive en la red privada** de Railway (sin dominio público). La web expone un **proxy server-side** (`/api/proxy/[...path]`) que reenvía a la API por la red interna. El navegador nunca habla con la API → se reutiliza el gate de contraseña existente y se elimina CORS.
3. **Conexión a Neon**: se normaliza `DATABASE_URL` para `asyncpg` (se quitan `sslmode`/`channel_binding` y se activa SSL vía `connect_args`), tanto en la app como en Alembic.
4. **Migraciones**: se aplican al arrancar (`alembic upgrade head` en `start.sh`), idempotentes.
5. **Salud**: `/health` verifica también la base de datos (200 sano / 503 degradado).
6. **Operación**: despliegue continuo al hacer push a `main`; escaneo de mercado diario por **cron** (solo propone sugerencias, no escribe precios).

## Alternativas consideradas

- **API pública + token bearer**: el token viajaría al navegador (visible) → seguridad débil. Rechazada.
- **API pública sin auth**: inaceptable (cualquiera cambiaría precios reales). Rechazada.
- **Nixpacks en vez de Dockerfile**: menos control del arranque/migraciones. Se prefiere Dockerfile explícito.
- **Postgres en el mismo Railway**: costaría más; Neon gratis ahorra y aísla la DB.

## Consecuencias

- **+** API no expuesta a internet; misma contraseña protege todo; sin CORS; imágenes pequeñas.
- **+** Despliegue reproducible y continuo; DB reconstruible desde Beds24 (fuente de verdad) sin backups en v1.
- **−** La web gana una capa de proxy (un route handler) y debe reenviar streaming (SSE) — complejidad menor y acotada.
- **−** Coste de Railway es por uso: requiere vigilar el consumo para no exceder el presupuesto.
