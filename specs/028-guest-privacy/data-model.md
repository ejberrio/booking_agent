# Data Model: Feature 028

## terms_acceptance (nueva)
| Campo | Tipo | Notas |
|---|---|---|
| id | int PK | |
| user_id | FK app_user, index | |
| version | str(20) | p. ej. `2026-10-14` |
| accepted_at | timestamptz | |
| created_at/updated_at | timestamptz | TimestampMixin |

Vigente = existe una fila con `version = LEGAL_VERSION`. Se conserva el historial.

## account (cambio)
- `status`: + `deleted` (lápida tras la supresión; `name = ""`, sin usuarios ni datos).

## booking (sin cambio de esquema)
- `guest_name`: se vacía cuando `check_out < hoy - 365`.

## auth_token (sin cambio)
- Nuevo propósito `delete_account` (código de 6 dígitos como hash, 15 min).
