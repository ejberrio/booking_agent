# Contrato: API pública (sin sesión; solo vía servidor web con `x-client-ip`)

- `GET /public/municipalities?q=sab` → `[{code, name, department, label}]` (máx. 20; sin q: vacío).
- `POST /public/report` `{municipality_code, weekday_price, weekend_price?, unit_kind?, currency?, language?}` →
  `{token, municipality, horizon_days:180, status: ok|no_events|budget_exhausted, events:[{name, start_date, end_date, relevance, kind, location, base_price, suggested_price, pct}] (máx. 3), total_events, registration: {open, full}}`.
  Errores: 400 `invalid_data`, 404 `unknown_municipality`, 429 `rate_limited`.
- `POST /public/waitlist` `{email, consent:true, language?, municipality_code?}` → `{ok:true}` (misma respuesta si ya existe). 400 sin consentimiento; 429.
- `POST /public/visit` → `{ok:true}` (cuenta una visita).
- `GET /auth/registration-status` → `{open, full}` (open = encendido y con cupo).
- Registro (`POST /auth/register`, Google start) aceptan `report` (token) opcional.

Con sesión:
- `GET /report/mine` → `{municipality, prices, events:[…todos…], generated_at}` o 404 si la cuenta no viene de un informe.

Admin (plataforma):
- `GET /admin/beta` → `{enabled, quota, used, city_budget, metrics:[{day, key, value}] (30 días), waitlist:[{id, email, language, municipality, created_at}]}`.
- `PATCH /admin/beta` `{enabled?, quota?, city_budget?}`.
- `POST /admin/waitlist/{id}/invite` → crea invitación, envía el correo con el enlace y borra la entrada.
- `DELETE /admin/waitlist/{id}`.
