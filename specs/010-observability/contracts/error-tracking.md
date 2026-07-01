# Contrato: Seguimiento de errores (Sentry)

## API (FastAPI)
- `sentry_sdk.init(dsn=SENTRY_DSN, environment=ENVIRONMENT, release=<version>,
  traces_sample_rate=0.0, send_default_pii=False)` al arrancar.
- `dsn` None → no-op (la app arranca y opera normal).
- Captura automática de excepciones no controladas (integración FastAPI).
- No envía PII ni secretos (el adapter redacta tokens; no se adjuntan cuerpos).

## Web (Next.js)
- `Sentry.init({ dsn, environment, tracesSampleRate: 0 })` en `instrumentation.ts` (servidor) y
  `instrumentation-client.ts` (cliente). Sin DSN → no-op.
- Sin `withSentryConfig` ni subida de source-maps en v1.

## Reglas
- Best-effort: si Sentry no responde, no rompe ni ralentiza las peticiones del usuario.
- Cero secretos/PII en los eventos.
- DSN por variable de entorno; lo crea el operador.
