# Research & Decisiones — Observabilidad

Formato: Decisión / Razón / Alternativas.

## 1. Seguimiento de errores — Sentry (no-op sin DSN)
- **Decisión**: API con `sentry-sdk[fastapi]`: `sentry_sdk.init(dsn=settings.sentry_dsn,
  environment=settings.environment, release=app.version, traces_sample_rate=0.0,
  send_default_pii=False)`. Si `dsn` es None → `init` es **no-op** (la app arranca igual).
  La integración FastAPI captura excepciones no controladas automáticamente.
  Web con `@sentry/nextjs` inicializado en `instrumentation.ts` (servidor) y
  `instrumentation-client.ts` (cliente); no-op si el DSN no está.
- **Razón**: estándar, SDKs maduros, no-op nativo sin DSN, 0% trazas (mínima cuota, clarify).
- **Alternativas**: montar logging→alerta propio (más trabajo, menos útil); GlitchTip/self-host
  (innecesario para single-tenant). Rechazadas.
- **Sin secretos/PII**: `send_default_pii=False`; el adapter Beds24 ya redacta tokens; no se
  envían cuerpos de request. Opcional `before_send` para depurar headers sensibles.

## 2. Sentry en la web — integración ligera (sin withSentryConfig)
- **Decisión**: usar los hooks `instrumentation`/`instrumentation-client` de Next 15 para
  `Sentry.init`, SIN envolver `next.config` con `withSentryConfig` ni subir source-maps en v1.
- **Razón**: captura errores con mínima fricción; evita acoplar el build/Docker y no requiere
  auth-token de Sentry para source-maps. (Las trazas legibles del cliente bastan para v1.)
- **Alternativas**: wizard completo de `@sentry/nextjs` (source-maps, tunnel) → más complejidad
  de build; se difiere.

## 3. Logging estructurado de la API — middleware key=value
- **Decisión**: middleware ASGI/HTTP que mide duración y loguea
  `method=GET path=/pricing/calendar status=200 ms=45` (path SIN query para no filtrar nada).
  Errores: log con traza (`exc_info`). Nivel desde `settings.log_level` (default INFO).
  Formato de logging configurado al arrancar (handler a stdout → lo recoge Railway).
- **Razón**: legible en el visor de Railway (clarify), sin agregador propio.
- **Alternativas**: JSON estructurado (menos legible a simple vista) — rechazado en clarify;
  structlog (dependencia extra) — innecesario para el formato simple.

## 4. Endpoint /status — resiliente y con Beds24 cacheado
- **Decisión**: `GET /status` devuelve `{version, db: up|down, beds24: connected|error|unknown,
  open_issues: N}`. Cada comprobación va en try/except con timeout corto; si falla, marca esa
  parte degradada y sigue (nunca cuelga). El chequeo de Beds24 es **en vivo pero cacheado ~5 min**
  en memoria de proceso (timestamp + último resultado); `open_issues` = conteo de `SyncIssue`
  abiertas (consulta barata). `/health` se mantiene como liveness básico para Railway.
- **Razón**: foto rápida del sistema sin consumir cuota (clarify) ni colgarse (FR-007).
  Cache en proceso basta (1 réplica).
- **Alternativas**: chequear Beds24 en vivo cada llamada (lento/cuota) o no chequear (menos
  preciso) — rechazadas en clarify a favor del cacheado.
- **Protección**: `/status` queda tras el proxy/login como el resto (FR-010); la API es privada.

## 5. Configuración
- **Decisión**: nuevas variables: `SENTRY_DSN` (api, opcional), `NEXT_PUBLIC_SENTRY_DSN`/`SENTRY_DSN`
  (web, opcional), `LOG_LEVEL` (api, default INFO). Las pone el operador en Railway; el DSN de
  Sentry lo crea el host (la app no gestiona la cuenta).
- **Razón**: FR-002/FR-009 (no-op sin credencial; credencial por entorno).
