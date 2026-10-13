# Ambiente de pruebas (staging)

Objetivo: desarrollar y probar las fases comerciales (épica #156) **sin tocar producción**
(staylever.com y la app Android que el host usa a diario para su apartamento).

| | Producción | Pruebas |
|---|---|---|
| Web | staylever.com + APK | dominio de Railway del ambiente `staging` (franja amarilla "AMBIENTE DE PRUEBAS") |
| Código | rama `main` | rama en desarrollo (hoy `026-multitenant-accounts`) |
| Base | Neon, rama `main` | Neon, rama `staging` (copia instantánea de producción) |
| Beds24 / Booking / Airbnb | reales | **simulados** (`CHANNEL_MODE=simulated`): nunca se lee ni se escribe nada real |
| Avisos al celular | sí | **no** (el modo simulado los apaga) |
| Escaneo diario (`scan`) | sí | **no** (servicio sin desplegar en staging) |

Doble seguro contra tocar lo real: (1) `CHANNEL_MODE=simulated` hace que la API **nunca** construya
el adaptador de Beds24 ni envíe avisos; (2) staging usa otro `SECRET_KEY`, así que los secretos
copiados con la base (token de Beds24, Firebase) quedan **ilegibles**, y no lleva variables
`BEDS24_*`.

## Montaje (una vez)

Los **secretos** (cadena de conexión, claves, contraseñas) los pega siempre el host; el resto
puede hacerlo el copiloto.

1. **Neon** (console.neon.tech, proyecto de StayLever) → *Branches* → *Create branch*:
   nombre `staging`, padre `main` (o `production`), datos actuales ("Head"). Copiar su
   *connection string* (Dashboard → Connect, rama `staging`).
2. **Railway** (proyecto `booking-ai-agent`) → selector de ambientes → *New Environment* →
   **vacío** (no "duplicar": duplicar copiaría la base y el token de producción) → nombre `staging`.
3. En `staging`, servicio **api** → *Variables*:
   - Secretos (el host): `DATABASE_URL` = cadena de la rama `staging` de Neon; `SECRET_KEY` = una
     clave nueva (`openssl rand -hex 32`); `OPENAI_API_KEY` (opcional, para probar el chat).
   - Normales: `CHANNEL_MODE=simulated`, `ENVIRONMENT=staging`, `AUTH_MODE=legacy`,
     `BEDS24_API_VERSION=v2`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_MODEL_ACTIONS` (mismos de
     producción), `PORT=8000`.
   - **Sin** `BEDS24_REFRESH_TOKEN`, `BEDS24_PROP_ID`, `BEDS24_ROOM_ID`, `SEARCH_API_KEY`.
4. Servicio **web** → *Variables*: `API_INTERNAL_URL=http://api.railway.internal:8000`,
   `STAYLEVER_ENV=staging`, y `APP_PASSWORD` = una contraseña **distinta** a la de producción
   (el host).
5. **api** y **web** → *Settings* → *Source*: rama `026-multitenant-accounts` (luego, la rama de
   cada fase). **web** → *Networking* → *Generate Domain* (dominio de Railway).
6. Servicio **scan** en `staging`: no desplegarlo (sin cron).
7. Desplegar `api` (aplica migraciones sobre la rama de Neon) y luego `web`.

## Uso

- Cada push a la rama en desarrollo redespliega staging. Allí se prueba con los datos reales
  copiados; el host puede entrar desde el navegador del celular (no desde la app).
- Refrescar los datos: en Neon, *Reset from parent* sobre la rama `staging` (vuelve a copiar
  producción) y redesplegar `api`.
- Costo: la rama de Neon entra en el plan gratis; staging en Railway consume poco y puede
  apagarse (*Remove* de los despliegues) entre fases.

## Paso a producción (cada entrega)

1. Verificada en staging y aprobada por el host.
2. Copia instantánea: en Neon, rama `antes-de-<entrega>` desde `main` (restaurable en segundos).
3. Fusionar el PR → Railway despliega producción; el copiloto verifica calendario, precios,
   webhook y aviso de prueba.
4. Si algo falla: Railway → *Redeploy* del despliegue anterior y, si hubo migración, restaurar la
   rama de Neon. Los interruptores (`AUTH_MODE`) permiten volver atrás sin redesplegar.
