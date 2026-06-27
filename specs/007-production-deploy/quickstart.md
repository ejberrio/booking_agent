# Quickstart / Runbook — Despliegue en Railway + Neon

Guía del operador para llevar Booking_AI_Agent a producción. (La versión final vivirá en `docs/deploy.md`.)
Tú haces: crear cuentas, configurar variables y pulsar deploy. El repo aporta los Dockerfiles, el proxy y este runbook.

## 0. Prerrequisitos

- Cuenta en **Neon** (gratis) y en **Railway** (plan Hobby ~US$5/mes).
- El repo `ejberrio/booking_agent` con la rama `main` al día (incluye esta feature mergeada).
- Tener a mano los secretos: `OPENAI_API_KEY`, `SEARCH_API_KEY` (Tavily), `BEDS24_REFRESH_TOKEN`, `BEDS24_PROP_ID`/`ROOM_ID`, y una `APP_PASSWORD` y `SECRET_KEY` nuevas.

## 1. Base de datos (Neon)

1. Crea un proyecto en Neon (región cercana, p. ej. US East).
2. Copia la **connection string** (formato `postgresql://user:pass@host/db?sslmode=require`).
3. Guárdala para usarla como `DATABASE_URL` (el código la normaliza a asyncpg + SSL; puedes pegarla tal cual).

## 2. Proyecto en Railway

Crea un proyecto y dentro **tres servicios** desde el mismo repo (GitHub):

### 2a. Servicio `api` (privado)
- Root Directory: `apps/api` · Builder: Dockerfile.
- **No** generes dominio público (deja solo red privada). Anota su host interno (p. ej. `api.railway.internal`).
- Variables: las de la tabla `api` en `contracts/environment.md` (incluida `DATABASE_URL` de Neon, `ENVIRONMENT=production`, `BEDS24_API_VERSION=v2`, `BEDS24_REFRESH_TOKEN`, etc.).
- Healthcheck path: `/health`.

### 2b. Servicio `web` (público)
- Root Directory: `apps/web` · Builder: Dockerfile.
- Genera **dominio público** (será tu URL).
- Variables: `API_INTERNAL_URL=http://api.railway.internal:8000`, `APP_PASSWORD`, `SECRET_KEY`/`SESSION_SECRET`.

### 2c. Servicio `scan` (cron)
- Mismo repo/imagen que `api` (Root `apps/api`), **Cron Schedule** `0 13 * * *`.
- Start command: `python -m scripts.scan_daily`.
- Variables: las mismas que `api` (DB, OpenAI, Tavily, Beds24).

## 3. Despliegue continuo

- Conecta cada servicio a la rama `main`. A partir de aquí, **cada push a `main` redepliega** automáticamente (la `api` corre `alembic upgrade head` al arrancar).

## 4. Primer deploy

1. Dispara el deploy de `api`, `web` y `scan` (o haz un push a `main`).
2. La `api`, al arrancar, aplica las migraciones (esquema creado en Neon).

## 5. Verificación post-deploy (checklist)

- [ ] **API sana**: el healthcheck del servicio `api` está verde (responde `/health` = `healthy`, `db: up`).
- [ ] **Esquema aplicado**: en Neon, las tablas existen (o `alembic current` = head en los logs del deploy).
- [ ] **Web carga**: abre la URL pública → te pide contraseña → ingresas `APP_PASSWORD` → ves el panel.
- [ ] **Proxy OK**: el calendario/chat cargan datos (la web está hablando con la API por la red privada).
- [ ] **Beds24 en prod**: dispara la prueba de conexión (desde la UI o `POST /sync/test` vía proxy) → confirma tu propiedad real.
- [ ] **Datos**: corre `POST /sync/import` (vía la web) para traer precios/reservas reales a la nueva DB.
- [ ] **Cron**: verifica en los logs de `scan` que la corrida diaria ejecuta y registra sugerencias.

## 6. Operación

- **Actualizar**: push a `main` → redeploy automático.
- **Cambiar un secreto**: edítalo en Railway (variable del servicio) → redeploy. Nunca en el repo.
- **Recuperar datos**: si la DB se pierde/corrompe, re-importa desde Beds24 con `POST /sync/import` (fuente de verdad).
- **Costo**: revisa el uso en el dashboard de Railway; si sube, reduce recursos o duerme la web.

## 7. Notas

- Solo la `web` es pública; la `api` no es alcanzable desde internet (más segura).
- El token V2 de Beds24 se renueva solo; basta `BEDS24_REFRESH_TOKEN` en `api` y `scan`.
- Sin respaldos programados en v1 (decisión registrada); la DB es reconstruible desde Beds24.
