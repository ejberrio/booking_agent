# Contrato: Variables de entorno por servicio

Todas se definen como **Railway service variables** (nunca en el repo). Secreto = no debe aparecer en logs ni en el bundle del navegador.

## Servicio `api` (FastAPI, privado)

| Variable | Secreto | Requerido | Notas |
|----------|:------:|:--------:|-------|
| `DATABASE_URL` | ✅ | ✅ | Cadena de Neon (`postgresql://…?sslmode=require`); el código la normaliza a `asyncpg` + SSL |
| `SECRET_KEY` | ✅ | ✅ | Clave de la app (sesiones/firmas) |
| `ENVIRONMENT` | ❌ | ✅ | `production` |
| `OPENAI_API_KEY` | ✅ | ✅ | LLM |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_MODEL_ACTIONS` | ❌ | ⬜ | Defaults: openai / gpt-4o-mini / gpt-4o |
| `SEARCH_PROVIDER` / `SEARCH_API_KEY` | ✅(key) | ✅ | Tavily |
| `CHANNEL_MANAGER` | ❌ | ✅ | `beds24` |
| `BEDS24_API_VERSION` | ❌ | ✅ | `v2` (escritura) |
| `BEDS24_REFRESH_TOKEN` | ✅ | ✅ | Token V2 (se renueva solo) |
| `BEDS24_PROP_ID` / `BEDS24_ROOM_ID` | ❌ | ✅ | Identificadores (no secretos) |
| `BEDS24_API_KEY` / `BEDS24_PROP_KEY` | ✅ | ⬜ | Solo si se usa V1 para lectura/diagnóstico |
| `CORS_ORIGINS` | ❌ | ⬜ | No necesario con proxy (same-origin); dejar vacío o dominio web |

> La `api` **no** define dominio público en Railway (solo red privada). Railway le asigna `$PORT`.

## Servicio `web` (Next.js, público)

| Variable | Secreto | Requerido | Notas |
|----------|:------:|:--------:|-------|
| `API_INTERNAL_URL` | ❌ | ✅ | URL interna de la API, p. ej. `http://api.railway.internal:8000`. **Solo server-side** (no `NEXT_PUBLIC_`) |
| `APP_PASSWORD` | ✅ | ✅ | Contraseña del gate de la web (ya existente) |
| `SECRET_KEY`/`SESSION_SECRET` | ✅ | ✅ | Firma de la cookie de sesión (según implementación actual del login) |

> Con el proxy, **no** se usa `NEXT_PUBLIC_API_URL` (el navegador llama a `/api/proxy`). Railway le asigna `$PORT` y un dominio público.

## Servicio `scan` (cron)

- Reutiliza la **imagen y variables de `api`** (DB, OpenAI, Tavily, Beds24). Comando: `python -m scripts.scan_daily`. Schedule: `0 13 * * *` (UTC).

## Reglas

- Ningún secreto se hardcodea ni se loguea (FR-012, SC-007).
- Variables compartidas (`DATABASE_URL`, claves de IA/búsqueda/Beds24) deben ser idénticas en `api` y `scan`.
- Cambiar un secreto = actualizar la variable en Railway y redeploy; no requiere tocar el repo.
