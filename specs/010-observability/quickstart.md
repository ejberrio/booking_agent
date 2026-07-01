# Quickstart — Observabilidad

## Errores (Sentry)
1. Con `SENTRY_DSN` configurado: provocar un error de prueba (un endpoint/acción que lance una
   excepción de prueba) → aparece en Sentry con entorno, versión y contexto, sin secretos.
2. Sin `SENTRY_DSN`: la app arranca y opera con normalidad (no-op), 0 fallos por ello.

## Logging
- Hacer varias peticiones (alguna que falle) y ver en los logs de Railway una línea por petición
  `method=… path=… status=… ms=…`; los errores con traza. Revisar que no hay secretos.

## Estado
- `GET /status` (vía el proxy, autenticado) devuelve `version`, `db`, `beds24` (cacheado) y
  `open_issues`. Con la DB caída → `db=down`; con incidencias abiertas → `open_issues` coincide.
- `/health` sigue respondiendo como liveness básico (Railway).

## Verificación (prod, vía proxy con cookie de sesión)
```bash
WEB=https://web-production-dfcaf.up.railway.app
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/status"   # version/db/beds24/open_issues
```
