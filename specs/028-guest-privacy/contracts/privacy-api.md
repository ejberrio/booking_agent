# Contrato: Feature 028

## API (con sesión)
| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /auth/me` | — | + `user.terms_required: bool`, `legal_version` |
| `POST /auth/terms/accept` | `{version}` | `200` · `409 {"code":"version_mismatch"}` si no es la vigente |
| cualquier otra ruta con sesión | — | `403 {"code":"terms_required"}` si falta aceptar |
| `GET /account/export` | — | JSON `{exported_at, legal_version, account, user, tables:{nombre:[filas]}}` |
| `POST /account/delete-code` | — | `202` envía código por correo (solo usuarios sin contraseña) |
| `POST /account/delete` | `{account_name, password?, code?}` | `200` · `400 {"code":"name_mismatch"|"invalid_credentials"}` · `409 {"code":"protected"}` (cuenta nº 1) |

## API (sin sesión)
- `POST /auth/register`, `POST /auth/claim`: + `accept_terms: true` obligatorio (`400 {"code":"terms_required"}`).
- `POST /auth/google/start`: + `accept_terms` (se guarda en el estado; al crear o vincular se registra la aceptación si vino marcada).

## Web
- Páginas públicas `/terms`, `/privacy`. `/api/auth/terms` (POST, reenvía con la cookie). `/api/account/export` (descarga con `content-disposition`).
