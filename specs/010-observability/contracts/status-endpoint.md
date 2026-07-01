# Contrato: GET /status

Resumen de salud del sistema para el operador (vía el proxy autenticado). Distinto de `/health`
(liveness básico que usa Railway, que se mantiene).

## Respuesta (200)
```json
{ "version": "0.1.1", "environment": "production",
  "db": "up", "beds24": "connected", "open_issues": 0 }
```
- `db`: `up`/`down` (SELECT 1, con timeout).
- `beds24`: `connected`/`error`/`unknown` — chequeo en vivo **cacheado ~5 min**.
- `open_issues`: conteo de `SyncIssue` abiertas.

## Reglas
- Resiliente: cada comprobación en try/except con timeout; si una falla, se marca degradada y el
  endpoint responde igual (< 2 s). Nunca cuelga.
- Sin secretos en la respuesta.
- Protegido como el resto (tras el proxy/login). `/health` sigue público para el proveedor.
