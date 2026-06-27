# Contrato: `GET /health` (liveness + DB)

Usado por Railway como healthcheck del servicio `api` (por red interna) y por el operador para verificación post-deploy.

## Comportamiento

- Ejecuta una comprobación liviana de la base de datos (`SELECT 1`).
- **DB OK** → HTTP `200`:
  ```json
  { "status": "healthy", "db": "up" }
  ```
- **DB no responde** → HTTP `503`:
  ```json
  { "status": "degraded", "db": "down" }
  ```

## Reglas

- No expone detalles internos ni secretos (sin cadenas de conexión, sin trazas con credenciales).
- Debe ser rápido (timeout corto en la consulta) para no bloquear el healthcheck.
- Idempotente y sin efectos secundarios.

## Verificación

- `test_health.py`: con DB disponible → 200/`healthy`; con DB caída (sesión que lanza error) → 503/`degraded`.
