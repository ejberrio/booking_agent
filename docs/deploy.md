# Guía de despliegue — Railway + Neon

Despliegue de Booking_AI_Agent en producción: **web pública** (Next.js) + **API privada** (FastAPI) en Railway, **Postgres en Neon** (gratis). La web hace de proxy server-side hacia la API; el navegador nunca toca la API directamente.

> Tú (operador) creas las cuentas, pegas las variables y conectas el repo. El repositorio aporta Dockerfiles, el proxy, la normalización SSL y esta guía. **Los secretos van en Railway, nunca en el repo.**

Arquitectura (decisión en [ADR 0002](adr/0002-deploy-railway-neon.md)):

```
Navegador ──HTTPS──> [web (Next.js, público)] ──red privada──> [api (FastAPI, privado)] ──SSL──> [Neon Postgres]
                                                  ▲
                              [scan (cron diario)]┘  (reusa la imagen de api)
```

---

## 1. Base de datos en Neon

1. Crea un proyecto en [Neon](https://neon.tech) (región cercana, p. ej. *AWS us-east*).
2. Copia la **connection string** (`postgresql://USER:PASSWORD@HOST/DB?sslmode=require`).
3. Guárdala: será `DATABASE_URL`. **Puedes pegarla tal cual** — el backend la normaliza para asyncpg y activa SSL.

---

## 2. Proyecto en Railway

Crea un proyecto y conéctalo al repo `ejberrio/booking_agent` (rama `main`). Dentro, crea **tres servicios**.

### 2a. Servicio `api` (privado)

- **Root Directory**: `apps/api` · Builder: **Dockerfile** (ya hay `apps/api/railway.json`).
- **No generes dominio público** (deja solo *Private Networking*). Anota su nombre interno, p. ej. `api.railway.internal`.
- **Healthcheck**: `/health` (ya configurado en `railway.json`).
- **Variables** (Settings → Variables) — ver catálogo en [`contracts/environment.md`](../specs/007-production-deploy/contracts/environment.md):

  | Variable | Valor |
  |---|---|
  | `DATABASE_URL` | (cadena de Neon) |
  | `ENVIRONMENT` | `production` |
  | `SECRET_KEY` | (aleatorio largo) |
  | `OPENAI_API_KEY` | (tu key) |
  | `SEARCH_PROVIDER` / `SEARCH_API_KEY` | `tavily` / (tu key Tavily) |
  | `CHANNEL_MANAGER` | `beds24` |
  | `BEDS24_API_VERSION` | `v2` |
  | `BEDS24_REFRESH_TOKEN` | (token V2) |
  | `BEDS24_PROP_ID` / `BEDS24_ROOM_ID` | `337229` / `697411` |
  | `LLM_MODEL` / `LLM_MODEL_ACTIONS` | `gpt-4o-mini` / `gpt-4o` |

### 2b. Servicio `web` (público)

- **Root Directory**: `apps/web` · Builder: **Dockerfile**.
- **Genera dominio público** → será tu URL.
- **Variables**:

  | Variable | Valor |
  |---|---|
  | `API_INTERNAL_URL` | `http://api.railway.internal:8000` |
  | `APP_PASSWORD` | (contraseña del login) |

  > No se usa `NEXT_PUBLIC_API_URL`: el navegador llama a `/api/proxy` (mismo origen).

### 2c. Servicio `scan` (cron diario)

- Crea otro servicio desde el mismo repo, **Root Directory**: `apps/api` (reusa la imagen de la API).
- **Settings → Cron Schedule**: `0 13 * * *` (≈ 8:00 America/Bogotá).
- **Start Command** (override): `python -m scripts.scan_daily`.
- **Variables**: las mismas que `api` (DATABASE_URL, OpenAI, Tavily, Beds24).

  > El escaneo **solo propone sugerencias**; nunca cambia precios (Constitución III).

---

## 3. Despliegue continuo

Con los servicios conectados a `main`, **cada push a `main` redepliega** automáticamente. La `api`, al arrancar, ejecuta `alembic upgrade head` (migraciones idempotentes) antes de levantar uvicorn.

---

## 4. Primer despliegue

1. Dispara el deploy (o haz un push a `main`).
2. La `api` aplica las migraciones → crea el esquema en Neon.
3. Espera a que los 3 servicios queden *Active* / healthcheck verde.

---

## 5. Verificación post-deploy (checklist)

- [ ] **API sana**: healthcheck del servicio `api` en verde (`/health` → `{"status":"healthy","db":"up"}`).
- [ ] **Esquema aplicado**: en los logs del deploy de `api`, `alembic upgrade head` corrió sin error (o `alembic current` = head).
- [ ] **Web carga**: abre la URL pública → pide contraseña → ingresas `APP_PASSWORD` → ves el panel.
- [ ] **Proxy OK**: calendario y chat cargan datos (la web habla con la API por la red privada vía `/api/proxy`).
- [ ] **Beds24 en prod**: desde la UI, la prueba de conexión (o `POST /sync/test` vía proxy) confirma tu propiedad real.
- [ ] **Datos iniciales**: corre `POST /sync/import` (vía la web) para traer precios/reservas reales a Neon.
- [ ] **Cron**: en los logs del servicio `scan`, la corrida diaria ejecuta y registra sugerencias.

---

## 6. Operación

- **Actualizar**: push a `main` → redeploy automático con migraciones.
- **Cambiar un secreto**: edítalo en Railway (variable del servicio) → redeploy. Nunca en el repo.
- **Recuperar datos**: si Neon se pierde/corrompe, re-importa desde Beds24 con `POST /sync/import` (fuente de verdad). Sin backups programados en v1.
- **Costo**: revisa el uso en el dashboard de Railway (plan Hobby por uso); Neon es gratis. Si sube, reduce recursos o duerme la web.

---

## 7. Notas de seguridad

- Solo la `web` es pública; la `api` no es alcanzable desde internet.
- El login (cookie `session`) protege también `/api/proxy/*` vía el `middleware` de Next.
- El token V2 de Beds24 se renueva solo; basta `BEDS24_REFRESH_TOKEN` en `api` y `scan`.
- Ningún secreto vive en el repositorio ni se escribe en logs.
