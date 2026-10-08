# Data Model: Reservas en tiempo real (020)

## WebhookEvent (NUEVA, `webhook_event`)

| Campo | Tipo | Nota |
|---|---|---|
| id | int PK | |
| received_at | datetime tz | default now |
| source | String(20) | `"beds24"` |
| result | Enum `webhookresult` | `accepted` · `ignored` · `rejected` · `failed` |
| booking_ref | String(40) nullable | id externo de la reserva (no es PII) |
| detail | String(200) nullable | motivo FIJO (p. ej. "clave inválida", "Beds24 no respondió (AuthError)"); nunca contenido del aviso |
| sync_run_id | int nullable | `sync_run` creado por el re-sync (si hubo) |

- Sin cuerpo, sin cabeceras, sin nombre de huésped.
- Purga: al insertar se borran eventos con `received_at` < ahora − 30 días.
- Migración `a4b5c6d7e8f9` (down `f3a4b5c6d7e8`): crea enum + tabla + índice por `received_at`.

## Secreto `beds24_webhook_key` (existente: SecretEntry)

- Nuevo nombre en la lista cerrada `SECRET_NAMES` (label "Clave de avisos de Beds24", servicio "Reservas en tiempo real", test `webhook`).
- Generado por `POST /hooks/beds24/key`; resto del ciclo igual que 017 (cifrado, pista, auditoría, quitar).

## Booking / CalendarDay (existentes)

Sin cambios de esquema: el aviso dispara `import_remote` sobre el rango, que actualiza estado/fechas/canal/huésped de las reservas y `units_available` del calendario. `is_blocked` (bloqueos manuales) no se toca.

## Estado de avisos (derivado)

`{configured, status: "unconfigured"|"active"|"idle"|"never", last_accepted_at, counts_7d: {accepted, ignored, rejected, failed}, endpoint_url, header_name}` — `idle` si hay clave y el último aceptado tiene > 7 días; `never` si hay clave pero nunca llegó uno.
