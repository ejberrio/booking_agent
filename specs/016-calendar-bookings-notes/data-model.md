# Data Model: Feature 016 — Detalle de reservas y notas del host

**UNA migración** `d1e2f3a4b5c6` (down `c9d0e1f2a3b4`): columna nueva en `booking` + tabla `calendar_note`.

## Booking (existente — una columna nueva)

| Campo nuevo | Tipo | Regla |
|---|---|---|
| guest_name | String(200), **nullable** | nombre compuesto reportado por el CM; NULL = el canal no lo dio ("sin nombre" en UI) |

Reglas de import (FR-001): crear → set; existente → actualizar solo si el remoto trae nombre no vacío ≠ local (el silencio remoto nunca borra); cuenta en `updated_count`.

## CalendarNote (NUEVA — app/models/calendar.py)

| Campo | Tipo | Regla |
|---|---|---|
| id | PK | |
| unit_type_id | FK unit_type, index | |
| date_from / date_to | Date NOT NULL | `date_from <= date_to`; día único = iguales |
| text | String(500) | no vacío tras strip; ≤500 |
| created_at / updated_at | TimestampMixin | |

Solapes permitidos sin límite (FR-006). Sin vínculo con el Channel Manager (FR-007). DELETE real.

## RemoteBooking (puerto — campo nuevo)

`guest_name: str | None = None` — token neutro; V2 compone `firstName + " " + lastName` (parciales OK, vacío → None); V1 legacy → None.

## Vistas derivadas (cliente)

- **Reservas de la noche `d`**: bookings confirmadas con `check_in <= d < check_out` (el día de salida no ocupa).
- **`noteDates: Set<fecha>`** y **notas de la selección**: notas con `date_from <= d <= date_to`.
