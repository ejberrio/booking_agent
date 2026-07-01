# Contrato: Logging de peticiones (API)

## Formato (una línea por petición)
```
method=GET path=/pricing/calendar status=200 ms=45
```
- `path` SIN query string (evita filtrar datos).
- En error no controlado: además del log de error con traza (exc_info), la línea registra
  `status=500`.
- Nivel desde `LOG_LEVEL` (default INFO); salida a stdout (la recoge Railway).

## Reglas
- Sin secretos (ni tokens, ni cabeceras de auth, ni cuerpos).
- Exactamente un registro por petición (sin duplicar).
- No rompe la petición si el logging falla (best-effort).
