# Operations Runbook — Booking_AI_Agent (producción)

Referencia rápida para operar la plataforma desplegada. Complemento de [`deploy.md`](deploy.md).

## URLs y proyecto

- **App (web pública)**: https://web-production-dfcaf.up.railway.app
- **Railway**: proyecto `booking-ai-agent` (3 servicios: `web` público, `api` privado, `scan` cron).
- **Base de datos**: Neon Postgres (connection string en las variables de Railway, NUNCA en el repo).
- **Repo**: `ejberrio/booking_agent`, rama `main`.

## Arquitectura (resumen)

```
Navegador ─HTTPS→ web (Next, público) ─red privada IPv6→ api (FastAPI, privado) ─SSL→ Neon
                                                  ▲
                                  scan (cron diario) ┘   (misma imagen que api: python -m scripts.scan_daily)
```
- El navegador NUNCA llama al `api` directo: la web hace de proxy (`/api/proxy/...`). El `api` no tiene dominio público.
- Login por contraseña (`APP_PASSWORD`); el middleware protege todo salvo `/login`.

## Despliegue (CD)

- **Automático**: cada push/merge a `main` redespliega los 3 servicios (GitHub-connected, root dirs `apps/api` / `apps/web` / `apps/api`). El `api` corre `alembic upgrade head` al arrancar.
- **Manual (CLI)**, si hace falta: `railway up ./apps/api --path-as-root --service api --ci` (o `apps/web`).

## Verificación rápida (vía el proxy, con cookie de sesión)

> El middleware solo exige que exista la cookie `session`, así que para chequeos se puede usar `session=ok`.

```bash
WEB=https://web-production-dfcaf.up.railway.app
curl -s -o /dev/null -w "login %{http_code}\n" "$WEB/login"                 # 200
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/health"                      # {"status":"healthy","db":"up"}
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/openapi.json" | jq .info.version
curl -s -X POST -H "Cookie: session=ok" "$WEB/api/proxy/sync/test"           # conexión Beds24
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/suggestions?status=proposed" # sugerencias
```

## Logs y estado (Railway CLI)

```bash
railway service list --json                          # estado/fuente de los 3 servicios
railway service status --service api --json          # deployment actual
railway logs -d --service api <deploymentId>         # runtime (uvicorn/alembic)
railway logs -b --service api <deploymentId>         # build
railway logs -d --service scan <deploymentId>        # corrida del cron
```
(Requiere `railway login` interactivo una vez en el equipo.)

## Disponibilidad (bloquear/abrir)

- **Por chat**: "cierra del 1 al 3 de julio" / "bloquea los fines de semana de agosto" / "vuelve a abrir el 2 de julio" → el agente propone → confirmas → se publica a Beds24 (numAvail). Nunca cierra noches con reserva confirmada.
- **Por calendario**: selecciona un rango → **Bloquear** / **Abrir** → preview → confirmar. Estados visuales: reservada (rojo), bloqueada (gris), promoción (ámbar), sin datos (—).
- Auditoría en `availability_change_log`; reversión = operación inversa (abrir deshace bloquear).

## Tareas comunes

- **Traer/actualizar datos reales** (precios + reservas desde Beds24): `POST /api/proxy/sync/import` con body `{"days":150}`.
- **Escaneo de mercado manual** (además del cron diario): redeploy del servicio `scan` o ejecutar `python -m scripts.scan_daily` con el entorno del `api`.
- **Recuperación ante pérdida de datos** (v1, sin backups): re-importar desde Beds24 con `/sync/import` (fuente de verdad).
- **Cambiar un secreto**: editar la variable en Railway (servicio correspondiente) → redeploy. Nunca en el repo.

## Variables de entorno

Catálogo completo en [`../specs/007-production-deploy/contracts/environment.md`](../specs/007-production-deploy/contracts/environment.md).
- `api`/`scan`: `DATABASE_URL`, `OPENAI_API_KEY`, `SEARCH_API_KEY`, `BEDS24_REFRESH_TOKEN`, `BEDS24_PROP_ID/ROOM_ID`, `BEDS24_API_VERSION=v2`, `ENVIRONMENT=production`, `SECRET_KEY`, `PORT=8000` (api).
- `web`: `API_INTERNAL_URL=http://api.railway.internal:8000`, `APP_PASSWORD`.

## Cron del scan

- Servicio `scan`, Cron Schedule `0 13 * * *` (≈ 8:00 America/Bogota), comando `python -m scripts.scan_daily`.
- Genera SOLO sugerencias (nunca cambia precios — Constitución III).

## Gotchas de Railway (ya resueltos en `main`)

- La red (pública y privada) es **IPv6**: el `api` bindea `uvicorn --host ::` y la `web` `HOSTNAME=::`.
- El servicio privado (`api`) **no** lleva healthcheck HTTP en `railway.json`.
- La `web` necesita carpeta `public/` para el `COPY` del Dockerfile.
- `DATABASE_URL` de Neon se normaliza en código para asyncpg + SSL (`sslmode=require` → cifrado sin verificación).

## Observabilidad

- **Errores (Sentry)**: crea un proyecto en Sentry y pon `SENTRY_DSN` en los servicios `api`/`scan` y `NEXT_PUBLIC_SENTRY_DSN` (cliente) + `SENTRY_DSN` (server) en `web`. **Sin DSN la app funciona igual** (no-op). Solo errores (0% trazas), sin PII.
- **Logs de la API**: una línea por petición en los logs de Railway: `method=GET path=/pricing/calendar status=200 ms=45`. Nivel con `LOG_LEVEL` (default INFO).
- **Estado del sistema**: `GET /status` (vía el proxy autenticado) → `{version, environment, db, beds24, open_issues}`. El chequeo de Beds24 se cachea ~5 min. `/health` sigue como liveness básico para Railway.
  ```bash
  curl -s -H "Cookie: session=ok" "$WEB/api/proxy/status"
  ```

## Backups y restauración

**Modelo de datos y fuente de verdad.** Precios, disponibilidad y reservas son
**re-importables desde Beds24** (fuente de verdad vía Channel Manager). Lo que un
backup preserva de forma irremplazable es el **rastro de auditoría**: decisiones
del agente (`agent_action`), promociones (`promotion`), cambios de disponibilidad
(`availability_change_log`), incidencias de sincronización (`sync_issue`) y
escaneos de inteligencia (`intelligence_run`).

Por eso la política es en dos capas:

1. **Automático (plataforma):** Neon ya realiza backups automáticos y permite
   *restauración a un punto en el tiempo* (PITR) dentro de la ventana de tu plan.
   Es la primera línea de recuperación ante un fallo o borrado accidental.
2. **Copia lógica off-site (script):** `scripts/backup_db.py` genera un dump
   portable (`pg_dump -Fc`, comprimido) restaurable en cualquier Postgres.

### Generar un backup lógico

```bash
cd apps/api
export DATABASE_URL="postgresql://…neon.tech/neondb?sslmode=require"   # o el que uses
BACKUP_DIR=~/booking-backups BACKUP_RETENTION=7 uv run python -m scripts.backup_db
# → booking-YYYYMMDDTHHMMSSZ.dump  (retención: conserva los N más recientes)
```

Requiere `pg_dump` en el PATH (macOS: `brew install libpq`). El dump **no** se
versiona (`backups/` y `*.dump` están en `.gitignore`): guárdalo en un lugar
seguro (disco externo, almacenamiento en la nube).

### Restaurar (procedimiento probado)

```bash
# 1) Base destino (nueva o vacía)
createdb booking_restore
# 2) Restaurar el dump
pg_restore --clean --if-exists --no-owner \
  -d "postgresql://usuario@host:5432/booking_restore" \
  booking-YYYYMMDDTHHMMSSZ.dump
# 3) Verificar
psql "…/booking_restore" -c "SELECT version_num FROM alembic_version;"
psql "…/booking_restore" -c "SELECT count(*) FROM agent_action;"
```

> Nota: al restaurar un dump de Postgres 18 en una versión anterior puede
> aparecer un aviso ignorable sobre `transaction_timeout` (un `SET` no soportado);
> la restauración de datos y esquema se completa igual.

### Política de retención

- **Neon (PITR):** según la ventana del plan; primera línea de recuperación.
- **Dumps lógicos:** el script conserva los **últimos 7** por defecto
  (`BACKUP_RETENTION`); el operador decide dónde archivarlos y cuánto tiempo.
- **Datos re-derivables:** ante pérdida, precios/disponibilidad/reservas se
  recuperan re-importando desde Beds24 (no dependen del backup).

**Recomendación operativa:** ejecutar `backup_db.py` antes de cambios grandes
(migraciones, borrados masivos) y de forma periódica (p. ej. semanal) archivando
el dump fuera de Neon.
