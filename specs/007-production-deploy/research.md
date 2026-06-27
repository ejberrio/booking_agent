# Research & Decisiones — Despliegue (Railway + Neon)

Resuelve los "NEEDS CLARIFICATION" y fija el enfoque técnico. Formato: Decisión / Razón / Alternativas.

## 1. Topología en Railway: web pública, API privada

- **Decisión**: Tres servicios en un proyecto Railway: `web` (Next.js, **único con dominio público**), `api` (FastAPI, **sin dominio público**, solo red interna `*.railway.internal`), y `scan` (cron, reutiliza la imagen de `api`). Postgres en Neon (externo).
- **Razón**: Cierra el hueco de seguridad (la API no tiene auth propia). Al no exponer la API a internet y enrutar todo por la web, el gate de contraseña existente protege también la API y se elimina CORS. Coste mínimo (servicios pequeños).
- **Alternativas**: API pública + token bearer (token visible en el navegador → débil); API abierta (inaceptable: cualquiera cambiaría precios reales). Ambas rechazadas por seguridad.

## 2. Seguridad de la API: proxy server-side en Next

- **Decisión**: El navegador llama a rutas **relativas** `"/api/proxy/<path>"` de la propia web. Un route handler `app/api/proxy/[...path]/route.ts` reenvía server-side a `http://${API_INTERNAL_URL}/<path>` por la red privada. `lib/api.ts` cambia su base de `NEXT_PUBLIC_API_URL` a `"/api/proxy"`. El middleware de auth (cookie `session`) ya cubre `/api/proxy/*` (no está en la lista pública), así que solo usuarios autenticados pueden usar la API.
- **Razón**: Same-origin (sin CORS), API nunca expuesta, reutiliza el login existente sin tocar el modelo de auth. Soporta streaming (SSE de `/chat/stream`) reenviando el `ReadableStream` del upstream.
- **Alternativas**: Reescribir cada pantalla a Server Components con fetch directo (más invasivo); añadir auth propia en FastAPI (duplica el gate y complica el cliente). Rechazadas por simplicidad.
- **Notas de implementación**: el handler debe (a) preservar método, headers relevantes, query y body; (b) propagar status y body de respuesta tal cual; (c) soportar respuestas en streaming sin bufferizar; (d) leer `API_INTERNAL_URL` solo en servidor (nunca `NEXT_PUBLIC_*`).

## 3. Neon + asyncpg: SSL

- **Decisión**: Normalizar `DATABASE_URL` en un único helper usado por la app (`db/session.py`) y por Alembic (`migrations/env.py`): (a) forzar el driver `postgresql+asyncpg`; (b) **eliminar** parámetros estilo libpq que asyncpg no entiende (`sslmode`, `channel_binding`); (c) pasar `connect_args={"ssl": True}` (TLS) al crear el engine. Así el operador puede pegar la URL de Neon tal cual (con `?sslmode=require`).
- **Razón**: asyncpg no acepta `sslmode` en la query; falla con "unexpected keyword". Neon exige TLS. Centralizar evita divergencias app/migraciones.
- **Alternativas**: pedir al operador editar la URL a mano (frágil); usar `psycopg` sync para Alembic (otra dependencia/driver). Rechazadas.
- **Test**: `test_db_url_ssl.py` verifica que una URL con `sslmode=require` se normaliza (sin el parámetro) y produce `connect_args` con SSL.

## 4. Migraciones automáticas al desplegar

- **Decisión**: La imagen de `api` arranca con `scripts/start.sh`: `alembic upgrade head` y luego `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Idempotente; seguro ante reinicios.
- **Razón**: Garantiza el esquema al día en cada release sin pasos manuales (FR-004, FR-017).
- **Alternativas**: paso de "release" separado en Railway (más config); migrar a mano (rompe reproducibilidad). Rechazadas. Riesgo de carrera con réplicas: se asume **1 réplica** del servicio `api` (single-tenant), por lo que no hay migraciones concurrentes.

## 5. Imágenes de contenedor

- **API (Dockerfile, uv)**: imagen base Python que coincide con `requires-python` del proyecto; `uv sync --frozen --no-dev`; copia la app; `CMD ["sh","scripts/start.sh"]`. `.dockerignore` excluye `.venv`, `tests`, caches.
- **Web (Dockerfile, Next standalone)**: `next.config.ts` con `output: 'standalone'`; build multi-stage (deps → build → runtime node-alpine); runtime copia `.next/standalone`, `.next/static`, `public`; `CMD ["node","server.js"]` con `HOSTNAME=0.0.0.0` y `PORT=$PORT`.
- **Razón**: imágenes pequeñas (menor coste/arranque). Con el proxy, la web **ya no necesita** `NEXT_PUBLIC_API_URL` en build (usa ruta relativa) → build más simple y sin secretos en el bundle del navegador.
- **Alternativas**: Nixpacks autodetectado (menos control sobre el comando de arranque/migraciones). Se prefiere Dockerfile explícito por reproducibilidad.

## 6. `/health` con verificación de DB

- **Decisión**: `GET /health` ejecuta `SELECT 1`. Responde `{"status":"healthy","db":"up"}` con 200 si la DB conecta; `{"status":"degraded","db":"down"}` con **503** si no. Railway usa `/health` como healthcheck del servicio `api` (por red interna).
- **Razón**: Detecta DB caída/suspendida; cumple FR-010, SC-009.
- **Alternativas**: solo liveness (no detecta DB caída). Rechazada por la decisión de clarify.
- **Test**: `test_health.py` simula fallo de DB y espera 503/degraded.

## 7. Escaneo de mercado diario (cron)

- **Decisión**: Servicio `scan` en Railway con **cron schedule** (p. ej. `0 13 * * *` UTC ≈ 8:00 America/Bogota), que reutiliza la imagen de `api` con comando `python -m scripts.scan_daily`. Comparte las mismas variables de entorno (DB, OpenAI, Tavily, Beds24).
- **Razón**: Mantiene sugerencias frescas sin intervención (FR-016, SC-008), a coste casi nulo (corre y termina). **Constitución III**: el escaneo solo PROPONE sugerencias, no aplica precios.
- **Alternativas**: cron externo (GitHub Actions) que pegue un endpoint (más piezas y expone un endpoint); manual (no cumple "automático"). Rechazadas.

## 8. Despliegue continuo (push a main)

- **Decisión**: Integración nativa GitHub↔Railway. Cada servicio define su **Root Directory** (`apps/api` / `apps/web`) y *watch paths*; un push a `main` dispara build+deploy automático (incluye migraciones vía start.sh). El cron `scan` se redepliega con la misma imagen.
- **Razón**: CD simple y reproducible (FR-017, SC-005) sin pipeline propio (Simplicidad).
- **Alternativas**: GitHub Actions construyendo/desplegando (más mantenimiento); deploy manual (no continuo). Rechazadas.

## 9. Configuración y secretos

- **Decisión**: Todas las variables se definen como **Railway service variables** (no en el repo). El `.env` local sigue gitignored. Variables compartidas (DB, OpenAI, Tavily, Beds24) se replican en `api` y `scan`. La `web` recibe `API_INTERNAL_URL` (host privado de `api`) y `APP_PASSWORD`/`SECRET_KEY` para el login. Catálogo completo en `contracts/environment.md`.
- **Razón**: FR-005, FR-012, SC-007 (cero secretos en repo/logs).
- **Alternativas**: archivo `.env` subido (prohibido). Rechazada.

## 10. Recuperación de datos (v1)

- **Decisión**: Sin respaldos programados en v1. Ante pérdida de datos, re-importar desde Beds24 (`POST /sync/import`), fuente de verdad de precios y reservas (FR-018). Documentado en el runbook.
- **Razón**: La DB es derivada del Channel Manager; el coste/complejidad de backups no se justifica para single-tenant v1 (YAGNI).
- **Alternativas**: dumps periódicos a almacenamiento (más trabajo/coste); confiar solo en Neon (sin control). Diferidas a una feature futura si se requiere.

## Riesgos y mitigaciones

- **Neon autosuspend**: la primera petición tras inactividad puede tardar; el engine reconecta (pool_pre_ping). Mitigación: `pool_pre_ping=True` en el engine.
- **Coste Railway por uso**: vigilar el dashboard; servicios a 512 MB. Si se excede, dormir la web o reducir recursos.
- **NEXT_PUBLIC en build**: al pasar a proxy relativo se elimina la dependencia de inyectar la URL de la API en build (menos fricción).
- **Token V2 de Beds24**: el `refreshToken` se renueva solo (token 24h); el cron y la API comparten el mismo mecanismo. Asegurar que `BEDS24_REFRESH_TOKEN` esté en ambos servicios.
