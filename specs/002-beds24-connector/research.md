# Research — Conector Beds24

Formato: Decisión / Justificación / Alternativas.

## 1. Versión de API de Beds24 → V1 (JSON) con API Key de cuenta

- **Decisión**: API V1 JSON, autenticando con la `apiKey` de cuenta (Allow Writes = Yes). **Sin propKey** (la propiedad es de la cuenta).
- **Justificación**: Es lo que el host ya configuró; para una propiedad propia la API Key de cuenta basta para leer y escribir, sin gestión de refresh tokens ni propKey. Más simple (principio V).
- **Alternativas**: V2 (invite code → refresh token, scopes) — más moderno pero añade ciclo de tokens; queda como evolución futura detrás del mismo puerto. propKey por propiedad — innecesario para propiedad propia.

## 2. Cliente HTTP → httpx async

- **Decisión**: `httpx.AsyncClient` (ya es dependencia). Timeouts explícitos; un cliente por adaptador.
- **Justificación**: Async encaja con FastAPI; `httpx.MockTransport` permite tests sin red.
- **Alternativas**: requests (síncrono), aiohttp (otra dependencia).

## 3. Autenticación y secretos

- **Decisión**: La `apiKey` se lee de variables de entorno (`BEDS24_API_KEY`); en las peticiones V1 va en el objeto `authentication`. La DB guarda solo el **estado** de la conexión y una **referencia** (nombre de la variable), nunca el secreto. Los logs jamás incluyen la key.
- **Justificación**: FR-003/SC-005 (sin secretos en repo/logs/DB). Single-tenant → env es suficiente; un secret manager se añade al desplegar.
- **Alternativas**: guardar credencial cifrada en DB — innecesario para single-tenant local y añade gestión de claves de cifrado.

## 4. Endpoints V1 usados (mapeo)

- **Decisión**: `getProperties` (propiedades + habitaciones), `getRoomDates`/`getRoomDatesBulk` (precios y disponibilidad por habitación/fecha), `setRoomDates` (escribir precio/disponibilidad), `getBookings` (reservas). Detalle en `contracts/beds24-v1-mapping.md`.
- **Justificación**: Cubren lectura (propiedades/calendario/precios/reservas) y escritura de precios por día/rango.
- **Alternativas**: endpoints V2 equivalentes (si se migra a V2).

## 5. Escrituras idempotentes y verificadas

- **Decisión**: Tras `setRoomDates`, **re-leer** (`getRoomDates`) el rango para confirmar el valor aplicado (verificación). Reintentos con **backoff exponencial** ante errores transitorios y rate limiting; la operación es idempotente (fijar el mismo precio dos veces es inocuo). Fallos no verificados → `SyncIssue(write_unverified)`.
- **Justificación**: FR-007/FR-009/FR-010/SC-003/SC-007.
- **Alternativas**: confiar en la respuesta de escritura sin verificar (riesgo de inconsistencia silenciosa).

## 6. Política de reconciliación y fuente de verdad

- **Decisión**: Reservas y disponibilidad → **el remoto es la fuente de verdad** (se reflejan en local). Precios → el host los fija en la plataforma y se **publican** al remoto. Si al importar el precio remoto difiere del local, se crea `SyncIssue(price_discrepancy)` y **NO se sobrescribe** local sin decisión del host.
- **Justificación**: FR-011/FR-012/SC-004 (cero sobrescrituras silenciosas).
- **Alternativas**: "último en escribir gana" (riesgo de pisar cambios del host); descartado.

## 7. Auditoría: qué se audita y qué no

- **Decisión**: Las **publicaciones** reflejan cambios que el host ya hizo localmente (auditados por `pricing_service.set_base_price`). La **importación de baseline** (primer poblamiento de precios/calendario) hace **upsert directo** de `Rate`/`CalendarDay` **sin** crear `PriceChangeLog` (no es un cambio del host). Las divergencias posteriores se reportan como `SyncIssue`, no se aplican en silencio.
- **Justificación**: Evita ruido de auditoría en el baseline y respeta el principio III (solo cambios del host se auditan; divergencias se reportan).
- **Alternativas**: añadir `ChangeOrigin.sync` y auditar cada precio importado — genera cientos de entradas en el primer sync; se descarta por ruido (se puede reconsiderar si se requiere trazabilidad total del origen externo).

## 8. Programación de la sincronización

- **Decisión**: Sincronización **diaria por cron** invocando `scripts/sync_daily.py`; además **disparo manual** vía endpoint (`POST /sync/import`, `/sync/publish`). Sincronización **incremental** usando un cursor (marca de última modificación) guardado en `SyncRun`.
- **Justificación**: Simplicidad (sin scheduler embebido); FR-006/FR-013/FR-014.
- **Alternativas**: APScheduler/cola de tareas — innecesario para una propiedad y una corrida diaria.

## 9. Estrategia de pruebas (sin API real)

- **Decisión**: Tests del adaptador con `httpx.MockTransport` devolviendo respuestas V1 de ejemplo (getProperties/getRoomDates/setRoomDates/getBookings), incluyendo casos de error (auth inválida, rate limit, escritura no verificada). Tests del `sync_service` con un **adaptador falso** in-memory (implementa el puerto) para import/publish/reconcile.
- **Justificación**: Determinismo y cero dependencia de credenciales/red (principio IV). No se añade dependencia (MockTransport viene en httpx).
- **Alternativas**: respx (dependencia extra), VCR/cassettes (frágiles).

## Sin NEEDS CLARIFICATION pendientes

Las decisiones de auth (V1), frecuencia (diaria) y reconciliación (reportar sin sobrescribir) fueron confirmadas por el host.
