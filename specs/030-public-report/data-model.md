# Data Model: Feature 030

Tablas de plataforma (NO `AccountOwned`; ninguna guarda datos de cuentas salvo `public_report.account_id`).

- **city_scan**: `city` (PK, ciudad normalizada como `event.city`), `scanned_at`, `source` (daily | public), `events_found`.
- **public_report**: `id`, `token_hash` (único), `municipality_code`, `city`, `weekday_price`, `weekend_price?`, `currency`, `unit_kind?`, `language`, `created_at`, `account_id?` (al registrarse), `emailed_at?`. Sin IP ni correo.
- **waitlist_entry**: `id`, `email` (único), `language`, `municipality_code?`, `consent_at`, `created_at`. Se borra al invitar o a los 12 meses.
- **public_metric**: (`day`, `key`) PK, `value` — claves: visit, report, report_cached, city_search, signup_open, signup_from_report, waitlist.
- **public_quota**: (`day`, `visitor`, `kind`) PK, `count` — visitor = HMAC diario de la IP; se borran las de días anteriores.
- **account.signup_source**: `open` | `invite` | `admin` | NULL (cuentas anteriores).
- **platform_setting `registration_open`**: `{enabled: bool, quota: int=50, city_budget: int=20}`.
