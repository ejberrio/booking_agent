# Data Model — Observabilidad

**Sin entidades persistentes nuevas ni migraciones.** Se reutiliza `SyncIssue` (incidencias
de publicación) para el conteo del estado. Lo "nuevo" son formas de respuesta y configuración.

## Forma de GET /status
```json
{
  "version": "0.1.1",
  "environment": "production",
  "db": "up",                 // up | down
  "beds24": "connected",      // connected | error | unknown (cacheado ~5 min)
  "open_issues": 0            // conteo de SyncIssue abiertas
}
```
- HTTP 200 si todo ok; puede devolver 200 con campos "degradados" (db=down/beds24=error) para
  que el operador vea el detalle (no es un healthcheck binario).

## Configuración (variables de entorno)
| Variable | Servicio | Requerido | Notas |
|----------|----------|:--------:|-------|
| `SENTRY_DSN` | api (y web server) | ⬜ | sin él, Sentry no-op |
| `NEXT_PUBLIC_SENTRY_DSN` | web (cliente) | ⬜ | DSN del cliente (público por diseño) |
| `LOG_LEVEL` | api | ⬜ | default INFO |

## Cache en proceso (no persistente)
- `beds24_status`: { ok|error, checked_at } con TTL ~5 min; vive en memoria del proceso de la API.
