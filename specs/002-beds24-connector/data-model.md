# Data Model — Conector Beds24

Entidades **nuevas** de operación (las de dominio ya existen en la feature 001). PostgreSQL / SQLAlchemy 2.0. `id`, `created_at`, `updated_at` por `TimestampMixin`.

## Entidades

### ChannelManagerConnection
Representa la cuenta de Channel Manager conectada (single-tenant: una fila activa).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| provider | enum(beds24) | proveedor |
| status | enum(unconfigured, connected, invalid) | estado de la conexión |
| credentials_ref | str | **nombre de la variable de entorno** (p. ej. "BEDS24_API_KEY"), NUNCA el secreto |
| account_label | str? | etiqueta legible (no secreta) |
| last_verified_at | timestamptz? | última prueba de conexión exitosa |

### SyncRun
Una ejecución de sincronización (entrante o saliente).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| direction | enum(import, publish) | dirección |
| status | enum(running, success, partial, error) | resultado |
| started_at | timestamptz | |
| finished_at | timestamptz? | |
| created_count | int | entidades creadas |
| updated_count | int | entidades actualizadas |
| issue_count | int | nº de incidencias |
| cursor | str? | marca incremental (última modificación procesada) |

### SyncIssue
Error o discrepancia detectada durante una sincronización.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| sync_run_id | FK→SyncRun | |
| kind | enum(comm_error, auth_error, price_discrepancy, write_unverified, rate_limited) | tipo |
| entity_ref | str? | referencia a la entidad afectada (p. ej. "unit_type:1 date:2026-07-15") |
| detail | str | descripción (sin secretos) |
| status | enum(open, resolved) | |

## Relaciones y mapeo
- `SyncIssue.sync_run_id → SyncRun`.
- El mapeo con el remoto usa los `external_ref` ya presentes en `Property`, `UnitType`, `Booking` (feature 001); esta feature los puebla y mantiene.

## Reglas de validación / invariantes
1. Solo una `ChannelManagerConnection` activa (single-tenant).
2. `credentials_ref` nunca contiene el secreto, solo el nombre de la variable.
3. `SyncRun.status=partial` ⇔ `issue_count > 0` con algún éxito; `error` si nada se completó.
4. Una discrepancia de precio genera `SyncIssue(price_discrepancy, status=open)` y **no** modifica `Rate` local.
5. La importación de baseline hace upsert de `Rate`/`CalendarDay` **sin** `PriceChangeLog`.

## DTOs neutrales (no ORM — viven en `app/channels/base.py`)
- **RemoteProperty**(external_id, name, currency, rooms: list[RemoteRoom])
- **RemoteRoom**(external_id, name, units_count)
- **RemoteRate**(room_external_id, date, price, available)
- **RemoteBooking**(external_id, room_external_id, check_in, check_out, status)
- **WriteResult**(ok: bool, verified: bool, detail: str|None)
- **ConnectionInfo**(ok: bool, properties: list[RemoteProperty], detail: str|None)

Estos DTOs son la frontera provider-agnostic: el adaptador Beds24 los produce/consume; el `sync_service` los mapea a/desde los modelos de la feature 001.
