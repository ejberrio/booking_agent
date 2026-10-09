# Operations Runbook — Booking_AI_Agent (producción)

Referencia rápida para operar la plataforma desplegada. Complemento de [`deploy.md`](deploy.md).

## URLs y proyecto

- **App (web pública)**: https://staylever.com (dominio en Cloudflare, proxied → Railway `web`; SSL/TLS en "Full"). Dominio de Railway como respaldo: https://web-production-dfcaf.up.railway.app
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
WEB=https://staylever.com
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

## Promociones de precio vía API (feature 011)

Promociones = una oferta con nombre y **precio con descuento** sobre un rango de
fechas, publicada al Channel Manager como *fixed price*.

### Oferta destino (sin setup obligatorio)

Verificado en vivo (2026-07-01): **Beds24 asigna los fixed prices a la oferta pública
principal (`offerId=1`) sin importar el valor enviado** — el slot no es seleccionable
por API. Las promociones caen en la oferta pública 1 (la que ve el huésped), así que
**no hay que designar/crear nada en el panel**. `BEDS24_PROMO_OFFER_ID` es un override
opcional (default 1) por si el canal empezara a respetarlo.

### Uso

- **Web**: sección *Ofertas* → crear (ver propuesta → confirmar), listar y retirar.
- **Chat**: "crea una promoción del 15 al 31 de enero con 20% de descuento, mínimo 3
  noches", "¿qué promociones tengo?", "quita la promo de enero".
- El descuento se pide en % o precio; al canal se envía **precio absoluto** (se guarda
  también el %). El precio queda fijado al crear (si cambia el base, la lista lo señala).

### Retirada (la API no tiene DELETE)

"Retirar" **neutraliza** la promo (`roomPriceEnable=false`: deja de descontar) y la
oculta de las activas. Es reversible. Puede quedar un **registro neutralizado** en el
panel de Beds24 hasta que lo borres a mano (limpieza opcional): *Prices → Fixed Prices*.

### Verificación de escritura real (acotada, con confirmación del host)

1. Crear una promo de prueba en la oferta designada, **fechas lejanas** (+300 días) y
   descuento pequeño.
2. Verificar en la lista (o `GET /inventory/fixedPrices`) que existe con su `external_id`.
3. **Retirar** de inmediato (neutraliza) → deja de descontar.
4. (Opcional) borrar el registro neutralizado en el dashboard.

> Nunca dejar una promo de prueba descontando.

### Salvedad

Que la promoción aparezca como **deal NATIVO** de Booking (Genius/Basic Deal/Última
hora, con badge) depende del mapeo de tarifas del canal; la API gestiona la tarifa
lado Beds24. Los deals con badge se siguen creando en el panel de Beds24 / extranet.

## Conexión con Airbnb (Fase 2 · issue #86, 2026-07-02)

El mismo apartamento está ahora conectado a **Airbnb vía Beds24** (API oficial, cuenta
Airbnb `290392420`, listing `638897594982065399` mapeado al room 697411).

### Configuración (Beds24 → Channel Manager → Airbnb)

- **Sync Type = "Prices and Availability"**: Beds24 envía precios, disponibilidad,
  estancia mínima y preaviso, e importa reservas. Fotos, textos y **descuentos de
  Airbnb** (semanal 5%, mensual 25%) se siguen gestionando **en Airbnb**.
- **Pricing clásico Per Day** (NO Rate Plans: cambian toda la cuenta a inventory grid
  y no soportan modificaciones de reserva).
- **Moneda — CRÍTICO**: la API de Airbnb **NO soporta COP**. Config correcta en
  *Mapping → Property Settings*: `Currency = USD` + `Multiplier = *[CONVERT:COP-USD]`
  (Beds24 convierte con tasa de mercado; 350.000 COP → ~$102/noche). Con
  `Currency=COP` los precios llegan corruptos (~mitad). El huésped que paga en COP ve
  ~8% más por el margen cambiario de Airbnb sobre anuncios USD (inevitable); neto
  para el host sigue siendo mejor que Booking (comisión ~3% vs ~15%).
- **Dates with no Price = "Make unavailable"**: fechas sin precio cargado (hoy, desde
  el 13-feb-2027) aparecen cerradas en Airbnb → cargar precios antes de ese horizonte.
- Con la API solo funciona **Instant Book**.

### Qué es de quién

| Se gestiona en la app / Beds24 (fluye a AMBOS canales) | Se gestiona en Airbnb |
|---|---|
| Precios por día/rango | Fotos, textos del anuncio |
| Disponibilidad / bloqueos | Descuentos semanal/mensual y promociones de Airbnb |
| Estancia mínima (calendario + default del room = 2 noches) | Política de cancelación, reseñas |
| Promociones de precio (fixed prices) — ⚠️ aplican a los dos canales | |

### Aprendizajes operativos

- El botón **Connect** del Room Mapping solo aparece tras resolver los
  **"Fix Content Errors"** (aunque el sync no envíe contenido): Rack Rate > 0
  (`Channel Manager → Property Content → Room Content`, quedó 350000), descripción del
  room > 50 caracteres, y camas suficientes para la capacidad
  (`Properties → Rooms → Setup → edit bedrooms`; real: H1 doble, H2 camarote
  doble+sencilla, H3 sencilla = 6 personas).
- **Los bloqueos manuales de Airbnb NO se importan**: replicarlos en Beds24 ANTES de
  conectar (se hizo vía la app: jul 6 y oct 19-21). Las reservas de Airbnb sí se
  importan (`Import Existing Bookings`; estadías > 4 semanas no).
- El primer sync **pisa el calendario de Airbnb** con los datos de Beds24 (por diseño).
- Verificación: *Mapping → Update* (espera "Success") + *Check Connection Status*;
  `https://beds24.com/api/airbnb.com/showdata.php?roomid=697411` muestra exactamente
  qué se envía (incluido el multiplicador). Airbnb tarda minutos en aplicar.
- La escritura de `minStay` por **API v2** funciona: `POST /inventory/rooms/calendar`
  con `{"from","to","minStay"}` (se usó para poner mínimo 2 noches jul-2026→feb-2027).
- Reservas de Airbnb llegan por `GET /bookings` con su canal (`channel`/`referer`) —
  la app hoy las etiqueta como Booking: se corrige en la Feature 012 (issue #87).

## Multi-canal (Feature 012 · issue #87)

La app refleja la realidad multi-canal del Channel Manager (Booking.com + Airbnb):

- **Canal real por reserva**: cada reserva importada registra su canal de origen
  (`booking`/`airbnb`; origen desconocido o manual → `direct`). Beds24 lo reporta en
  `GET /bookings` (`channel`, fallback `referer`).
- **Corregir históricos**: re-importar desde Beds24 (Configuración → Sincronizar o
  `POST /sync/import`). El import actualiza el canal de reservas existentes mal
  etiquetadas sin duplicarlas (dedupe por referencia externa). OJO: los CAMBIOS DE
  ESTADO (cancelaciones remotas) NO se sincronizan aún — issue #91.
- **`CHANNELS_ACTIVE`** (default `booking,airbnb`): declara qué canales están
  conectados en Beds24. Quitar uno lo marca inactivo (sus reservas se conservan);
  el cambio se aplica en la siguiente sincronización. No hay detección automática
  (Beds24 no expone el estado de conexión por API).
- **`GET /status`** incluye `channels: [{kind, is_active, bookings}]` — canales y
  reservas confirmadas por canal. El dashboard web lo muestra en la tarjeta "Canales".
- **Agente**: conoce los canales activos ("¿qué reservas tengo de Airbnb?" filtra por
  canal) y recuerda que precios/disponibilidad/promos publican a TODOS los canales
  conectados a la vez (no por canal — el ajuste por canal es la Feature 013).

## Precio por canal (Feature 013 · issue #88)

- **Offset por canal**: recargo/descuento % del canal sobre el precio base (p. ej.
  Airbnb +8%), gestionado en Configuración → "Precio por canal" o por chat
  ("ponle +8% a Airbnb"), siempre con propuesta → confirmación → auditoría
  (`channel_offset_log`) → verificación. Se materializa como sufijo del **multiplier**
  del canal en Beds24 (`*[CONVERT:COP-USD]*1.08`): la conversión de moneda se preserva
  SIEMPRE; quitar el offset (0%) restaura la fórmula original exacta.
- **Booking vende al precio base**: su ajuste no es configurable (Beds24 no expone
  multiplier de Booking por API). Para mover el precio relativo, ajusta el base o el
  offset de Airbnb.
- **Precio efectivo mostrado** = base × (1 + offset%). La conversión de moneda es
  neutra en valor; el margen cambiario que Airbnb aplica al huésped (~8%) es suyo.
- **Alcance de promociones**: al crear una promoción de precio se puede limitar a
  Booking o Airbnb (checkboxes en Ofertas o `channels_scope` por chat); el preview y
  la lista SIEMPRE muestran el alcance. Sin elección = todos los canales (como antes).
- ⚠️ **Doble descuento**: no combinar un deal nativo (badge de Booking / descuento
  semanal-mensual de Airbnb) con una promoción de precio en las mismas fechas y canal.
  Nota: en Airbnb una promoción recibe ADEMÁS el offset del canal (allowMultiplier).
- Si la escritura del offset falla o no se verifica (endpoint Alpha de Beds24), queda
  una incidencia en /status (`open_issues`) y el estado local no miente.

## Sugerencias: acción única "Aprobar y aplicar" (Feature 014 · issue #95)

- Una sugerencia se resuelve con UNA acción: **Aprobar y aplicar** (aprueba + fija el
  precio + publica al canal + audita con enlace al cambio) o **Rechazar**. El paso
  intermedio "aprobar sin aplicar" y su ruta `POST /suggestions/{id}/approve` fueron
  retirados (2026-07-03); las `approved` históricas siguen siendo resolubles en ambos
  sentidos y aparecen en la lista de pendientes.
- Dónde: en el **calendario** (los días con sugerencia vigente llevan punto violeta;
  clic en el día → panel con precio actual vs sugerido, rango, confianza y racional) y
  en la página **Sugerencias** (pendientes = `proposed` + `approved`).
- **Días pasados nunca se tocan**: si el rango ya empezó, se aplica desde hoy
  (`applied_from` en la respuesta y aviso en la UI); si venció por completo → 409.
- **Fallo del canal**: 502, incidencia `comm_error` visible en /status y la sugerencia
  sigue pendiente (el estado local no miente; no queda nada aplicado a medias).
- Reintentar una ya resuelta → 409 con el estado real (sin doble aplicación).

## Deals nativos: registro manual + advertencia real (Feature 015 · issue #94)

- Los deals nativos (badge de Booking, semanal/mensual de Airbnb) **no tienen API**:
  se gestionan en los paneles (deep-links en Ofertas) y se **ANOTAN** en la app
  (Ofertas → "Deals nativos registrados": canal, nombre, %, vigencia — vacía =
  "siempre activo" — y activo sí/no). El registro es informativo: **no escribe nada
  al canal**; mantenerlo alineado con el panel es responsabilidad del host (~10 s).
- Con el registro al día: el calendario (y el dashboard) marcan los días en oferta
  (punto cian = deal nativo, ámbar = promoción de la app; clic → panel "Ofertas del
  día" con el detalle) y el preview de promociones avisa con el **deal concreto**
  si una promo solaparía fechas y canal (cero avisos falsos; no bloquea — combinar
  a propósito es decisión del host). La protección aplica también al agente (mismo
  preview).

## Detalle de reservas y notas del host (Feature 016 · issue #96)

- **Clic en un día reservado** → panel con huésped (si el canal lo reportó; "sin
  nombre" si no), canal, llegada → salida, noches, estado y referencia. El nombre
  es dato personal: solo se muestra dentro de la app y nunca aparece en logs (el
  middleware registra solo method/path/status). El día de salida no cuenta como
  ocupado por esa reserva. Para poblar nombres de reservas históricas: re-import.
- **Notas del host**: selecciona un día o rango en el calendario y guarda una nota
  (típico: el porqué de un bloqueo — "reserva personal de…"). Punto lima en los
  días cubiertos; editar/borrar desde el panel. Dato 100% local: nunca toca el
  Channel Manager. Máx 500 caracteres; los rangos pueden solaparse.

## Secretos desde la interfaz (Feature 017 · issue #99, ADR 0005)

- **Rotar**: Configuración → Secretos → pegar el valor nuevo → Guardar → Probar. Aplica de
  inmediato en la API (sin redeploy); el scan diario la toma en su próxima corrida. La UI es
  write-only: el valor nunca se muestra (solo "configurado · …últimos4 · origen").
- **Precedencia**: guardado en la app (BD, cifrado Fernet con clave derivada de SECRET_KEY) >
  variable de entorno de Railway. "Quitar" vuelve al valor de entorno.
- **Si se rota SECRET_KEY en Railway**: lo guardado queda "ilegible" (estado honesto, se usa el
  entorno como fallback); re-guardar cada secreto repara. La app nunca deja de arrancar por esto.
- **Auditoría**: últimos cambios (secreto, acción, pista, fecha) en la misma tarjeta — sin valores.
- Gestionables: OpenAI, Anthropic, Tavily, refresh token de Beds24. SECRET_KEY/APP_PASSWORD/
  DATABASE_URL siguen SOLO en Railway. El agente de chat no tiene acceso a los secretos.
- **Reconectar Beds24** (estado "invalid" / "Token not valid"): el refresh token de Beds24 vence
  si pasa 30 días sin usarse. En Beds24 → Settings → Marketplace → API → "Generate invite code" (READ:
  bookings, bookings-personal, inventory, properties, channels; WRITE: inventory, channels) y pegarlo en Ajustes → Secretos → "Canjear"; el
  servidor lo cambia por un refresh token nuevo. El cron diario (`scan`) sincroniza con Beds24
  antes de escanear, lo que además mantiene vivo el token.

## Motor de sugerencias v2 (Feature 018 · issue #98, ADR 0006)

- **Sugerencias por rango y explicables**: cada una dice sus factores (evento con nombre/lugar/
  fechas/fuente, ocupación, hueco, mercado con nº de muestras) y su % con signo. Las de BAJADA
  aparecen para noches libres a ≤14 días (tope −15%, nunca bajo el mínimo de la regla).
- **Sin duplicados**: un scan nuevo reemplaza (`superseded`) las pendientes solapadas y depura
  vencidas. Las resueltas no se tocan.
- **Contexto**: Configuración → "Sitios de interés" (POIs que dirigen las búsquedas; con fechas
  clave opcionales) y "Escaneo" (zona efectiva, consultas por corrida — cuidar los créditos de
  Tavily). La ubicación de la propiedad llega sola del re-import.
- **Mercado**: proveedor gratis (búsquedas dirigidas, mediana de tarifas encontradas); ancla el
  precio solo con ≥3 muestras; sin datos lo dice y no inventa. Proveedor pago enchufable
  (candidato: PriceLabs ~USD 10-20/mes — ADR 0006).

- **Peso del mercado** (decisión del host, 2026-10-08): el ancla de mercado pesa **50%** en fechas
  sin evento y **25%** en fechas con evento (75% tu precio con el alza del evento). Solo ancla si el
  precio de mercado está entre 0,5× y 2× tu tarifa; fuera de esa banda se informa como descartado.

## Sugerencias accionables: bloques y aplicación en lote (Feature 019)

- **Solo noches vendibles**: la pestaña Sugerencias oculta las noches con reserva confirmada,
  bloqueadas o con inventario 0 (el día de salida sí es vendible). Se calcula al consultar:
  si una reserva se cancela y la app sincroniza (cron, botón o chat), la sugerencia reaparece
  sin esperar al escaneo. El calendario sigue mostrando todos los marcadores.
- **Bloques**: por evento (une todas las fechas del mismo evento) o por periodo (días seguidos
  con la misma razón: "Libre próximo", "Ocupación alta"). Las bajadas se muestran igual que las
  subidas (decisión del host).
- **Lote**: marcar bloques o sugerencias → "Previsualizar" → una sola vista previa (noche, origen,
  antes → después, omisiones con motivo) → "Confirmar y publicar". "Aplicar solo esta" usa el
  mismo diálogo con una sola sugerencia.
- **Seguridad del lote**: si entre la vista previa y la confirmación cambió un precio, una reserva o
  el estado de una sugerencia → 409 "revísala de nuevo" y no se escribe nada. Se aplica por tramos
  (días seguidos con igual precio): si el canal falla en un tramo, ese tramo se revierte localmente,
  queda una incidencia `suggestion-batch:<fechas>` y sus sugerencias siguen pendientes.
- API: `GET /suggestions/blocks`, `POST /suggestions/batch/preview`, `POST /suggestions/batch/apply`
  (contrato en `specs/019-actionable-suggestions/contracts/`).

## Reservas en tiempo real: avisos de Beds24 (Feature 020 · issue #117)

- **Qué hace**: Beds24 (Booking Webhook V2) avisa a `https://staylever.com/api/hooks/beds24` cuando una
  reserva se crea, cambia de fechas/estado o se cancela; StayLever re-sincroniza ese rango desde Beds24
  (el aviso es solo una pista; Beds24 es la verdad) y el calendario/Sugerencias se actualizan en ~1 min.
  Nunca publica precios ni disponibilidad, ni toca bloqueos manuales. El cron diario sigue de respaldo.
- **Configurar (una vez)**: Ajustes → *Avisos en tiempo real* → "Generar clave" → copiar la línea
  `X-StayLever-Key: …` (se muestra UNA vez). Beds24 → Settings → Properties → Access → *Booking Webhook*:
  Version 2, URL `https://staylever.com/api/hooks/beds24`, Custom Header = la línea → Save.
- **Estados**: sin configurar · esperando el primer aviso · funcionando · sin actividad (7+ días sin
  avisos aceptados: revisar la configuración en Beds24 si sí hubo cambios de reservas).
- **Respuestas**: 200 aceptado/ignorado/fallido (fallido = Beds24 no respondió al re-sincronizar; el cron
  corrige), 401 clave incorrecta (rechazado), 503 sin clave (función apagada), 413 cuerpo > 256 KB.
- **Rotar la clave**: "Generar clave nueva" invalida la anterior al instante → actualizar el Custom
  Header en Beds24 en el mismo momento.
- **Privacidad**: el cuerpo del aviso (trae datos del huésped y tokens de pago) nunca se guarda ni se
  registra; la bitácora `webhook_event` solo guarda resultado, id de reserva y motivo fijo (30 días).

## Idiomas: español, inglés y portugués (Feature 021 · issue #124)

- **Selector**: menú lateral (escritorio y celular) y pantalla de login. Se recuerda con la cookie
  `lang` y, con sesión, en la preferencia del host (`GET/PUT /preferences`) para todos sus
  dispositivos. Primera visita: idioma del navegador si es es/en/pt; si no, español.
- **Variantes**: inglés de EE. UU. (en-US) y portugués de Brasil (pt-BR) — decisión del host. Moneda
  siempre COP; fechas y números con el formato del idioma.
- **Dónde están las traducciones**: `apps/web/lib/i18n/catalog/<área>.ts` (common, shell, dashboard,
  calendar, chat, suggestions, rationale, offers, connection, settings), cada archivo con `es`
  (referencia), `en` y `pt` lado a lado. Para corregir un texto, editar ese valor. Para agregar uno,
  añadirlo en `es` y en los otros dos: si falta en `en`/`pt`, `npx tsc --noEmit` / `npm run build`
  FALLAN (no se puede publicar a medias).
- **Mensajes del servidor**: la API sigue en español; `apps/web/lib/i18n/server-messages.ts` los
  traduce (texto exacto o patrón). Sin traducción → se ve en español.
- **Asistente**: el chat envía el idioma; el system prompt termina con "responde SIEMPRE en …" y los
  textos fijos (propuestas, confirmaciones, resultados) se traducen en `apps/api/app/agent/texts.py`
  conservando montos, fechas y nombres.
- **No se traduce**: nombres de eventos, notas del host, huéspedes, promociones y textos de Beds24.
- **Explicación de sugerencias**: se arma desde factores estructurados; las creadas antes de esta
  versión se ven en español hasta el siguiente escaneo diario.

## Bajadas como promoción (Feature 022 · issue #128)

- **Regla del host**: toda sugerencia que BAJA el precio se aplica como **promoción temporal** en
  Booking.com y Airbnb (nombre "StayLever · {bloque} {fechas}", marca "desde sugerencias" en Ofertas);
  el precio base no baja. Las subidas siguen cambiando el precio base. Un lote mixto se confirma una vez.
- **Precio mínimo por noche** (Ajustes): piso de esas promociones. Se calcula contra los descuentos que
  **siempre** pueden acumularse por canal (deals nativos con "se acumula siempre", p. ej. el 10 % móvil):
  `precio_promo ≥ max(mínimo, mínimo / (1 − descuento_canal))`. Si no cabe ≥ 1 %, la noche se omite.
  Los descuentos **condicionales** (semanal, mensual, anticipación) solo se informan.
- En Ofertas, cada deal nativo indica si "se acumula siempre" o es "condicional" (clic para cambiarlo).
- Si la promoción no se puede publicar, no queda creada (incidencia `suggestion-promo:<fechas>`) y la
  sugerencia sigue pendiente. Las promociones vencidas se ven como "finalizadas"; las de sugerencias sin
  noches libres muestran un aviso para retirarlas. Al retirar una, la sugerencia queda "aplicada" y la
  retirada consta en el historial de la promoción.
- El endpoint antiguo `POST /suggestions/{id}/apply` rechaza bajadas (deben pasar por la vista previa).

## Extender precios (Feature 023)

**Hallazgo (2026-10-08)**: en Beds24 había precio solo hasta el 12-feb-2027; desde el 13-feb las noches
estaban sin precio y cerradas (`numAvail 0`), así que no se podían reservar. El aviso de Beds24
("No price after 3 May 2027") no lo reflejaba.

- **Dónde**: Calendario → "Extender precios" (o el aviso del panel/calendario cuando quedan < 12 meses con precio).
- **Vista previa**: lee el calendario REAL de Beds24 desde hoy hasta la fecha final (por defecto hoy + 18 meses,
  máximo 24). Noches con precio → no se tocan; reservadas → se omiten; sin precio → reciben el precio de la
  plantilla; si además están cerradas se abren (1 disponible), salvo las que el host bloqueó desde la app.
- **Plantilla**: un precio por año-mes, propuesto con la mediana del mismo mes conocido sin noches de evento
  (si no hay, la mediana global), redondeada a miles. El host edita, excluye meses y puede sumar un % a viernes
  y sábado. Todo precio queda dentro de [mínimo, máximo] de la regla (hoy mínimo 230.000).
- **Confirmación**: huella de la vista previa (409 si algo cambió en Beds24) + casilla "Entiendo que se publicarán N noches".
- **Aplicación por mes**: auditoría local (`origin=extension` en precios y disponibilidad) + UNA escritura de
  calendario (`POST inventory/rooms/calendar` con varios tramos) + una relectura de verificación. Si un mes
  falla se deshace en la app, queda `SyncIssue price-extension:YYYY-MM` y los demás meses siguen; volver a
  extender lo reintenta (la vista previa vuelve a leer Beds24).
- **Costo en Beds24**: ≈ 1 lectura + 2 llamadas por mes (~31 para 18 meses). Sin costo adicional.
- **Precio 0**: la sincronización ya no guarda 0 para noches sin precio y la app muestra "—"; la migración
  `d7e8f9a0b1c2` borró las filas basura.
- **Aperturas no aplicadas (2026-10-09)**: Beds24 respondió `success` a `numAvail: 1` desde el 13-feb-2027 pero el
  inventario (Channel Manager → Channel Inventory) siguió en 0; ticket Beds24 #1064511. La app relee tras extender,
  guarda la disponibilidad REAL, avisa cuántas noches quedaron sin abrir y el panel muestra "Noches con precio que no
  se pueden reservar". Las escrituras de Beds24 pueden aplicarse con retraso (el precio de julio-2027 apareció minutos después).
- **Solución (2026-10-09)**: Beds24 ignora `numAvail: N` si su calendario YA dice N aunque el inventario que envía
  a los canales esté en 0 (responde `success` sin `"modified"`). Pasar por 0 y luego N lo corrige (probado por el
  host en el panel y luego por API para 2027-02-14..2028-04-09; Booking.com y Airbnb abrieron). El adaptador V2
  ahora reintenta solo con 0 → N cuando una APERTURA no queda al releer (nunca al bloquear).
