# Data Model: 025

## push_device (nuevo)
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| token | String(512) único | token FCM del teléfono |
| platform | String(16) | android / ios |
| model | String(120) null | p. ej. "Pixel 8" |
| app_version | String(32) null | |
| notify_bookings | bool = true | |
| notify_suggestions | bool = true | |
| enabled | bool = true | false si el token es inválido o el host lo quita |
| last_seen_at | datetime | se actualiza al registrar/abrir |
| last_error | String(300) null | |

## push_notification_log (nuevo)
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| kind | String(24) | booking_new, booking_modified, booking_cancelled, suggestions, test |
| ref | String(80) | external_ref de la reserva, id del escaneo |
| fingerprint | String(80) | `estado:check_in:check_out` o N |
| sent | int | teléfonos a los que se envió |
| created_at | datetime | |
Único (kind, ref, fingerprint).

## Eventos (no persistidos)
`BookingEvent {kind: new|modified|cancelled, ref, channel, check_in, check_out}`
