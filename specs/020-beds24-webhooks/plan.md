# Implementation Plan: Reservas en tiempo real (avisos de Beds24)

**Branch**: `020-beds24-webhooks` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-beds24-webhooks/spec.md` · issue #117

## Summary

Beds24 envía un **Booking Webhook** (Settings → Properties → Access) cuando una reserva se crea, cambia de disponibilidad o se cancela: versión 2 = `POST` con JSON `{timeStamp, booking{id, propertyId, roomId, status, arrival, departure, …}}`, reintenta si respondemos ≥ 400 y permite un **Custom Header** propio. Diseño:

1. **Entrada pública mínima en la web** (`POST /api/hooks/beds24`, fuera del middleware de sesión): limita tamaño, reenvía a la API privada SOLO la cabecera de clave y el cuerpo; no registra nada.
2. **API privada** (`POST /hooks/beds24`): valida la clave en tiempo constante contra el secreto `beds24_webhook_key` (Ajustes → Secretos); toma del cuerpo **solo** `booking.id`, `propertyId`, `arrival`, `departure` (nunca guarda el cuerpo: trae datos personales y tokens de pago) y **re-sincroniza desde Beds24** el rango afectado (± la estancia previa si cambió) con el `import_remote` existente → el Channel Manager es la fuente de verdad (FR-004), los duplicados y el desorden convergen solos (FR-008/009) y una clave filtrada solo podría provocar re-sincronizaciones, nunca inyectar datos.
3. **Bitácora mínima** `webhook_event` (resultado, referencia de reserva, motivo fijo) → estado en Ajustes (sin configurar / funcionando / sin actividad ≥ 7 días, último aceptado, conteos 7 días) + guía con la dirección y la línea de cabecera.
4. **Clave generada por la app y mostrada UNA vez** para pegarla en Beds24 (después solo pista de 4 caracteres; rotación = generar otra).

Sin escrituras al canal (solo lectura → sin preview/confirmación). El cron diario, el botón y el chat siguen como red de seguridad.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: existentes (FastAPI, SQLAlchemy async, httpx, Next route handlers); SIN dependencias nuevas
**Storage**: PostgreSQL / SQLite tests. **UNA migración** (`a4b5c6d7e8f9`, down `f3a4b5c6d7e8`): tabla `webhook_event`
**Testing**: pytest (canal falso para `import_remote`, ASGITransport para la ruta); web `npm run build`
**Target Platform**: Railway (`web` pública → `api` privada)
**Project Type**: monorepo web application
**Performance Goals**: responder a Beds24 en < 5 s (re-sync de un rango corto: 1 llamada de calendario + 1 de reservas); latencia total ≈ la de la cola de Beds24 (~1 min)
**Constraints**: API privada; secretos write-only (excepción documentada: la clave generada se muestra una sola vez); sin PII ni clave en logs; no tocar bloqueos manuales; no romper 276 tests
**Scale/Scope**: single-tenant; ~6 archivos API + ~4 web + 1 migración

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; investigación de Beds24 en research.md (wiki + OpenAPI V2 + panel del host) |
| II. Provider-agnostic | ✅ el endpoint es específico de Beds24 (como su adaptador), pero el procesamiento es "re-sincroniza el rango" vía el puerto `ChannelManager` (`import_remote`); otro CM solo necesitaría su propio parser de aviso |
| III. Human-in-the-loop | ✅ los avisos solo LEEN/sincronizan (igual que el cron); jamás publican precios/disponibilidad ni tocan bloqueos |
| IV. Tipado y pruebas | ✅ tests de autenticación (sin clave/incorrecta/rotada), idempotencia, desorden, aviso incompleto, fallo del CM, ajeno a la propiedad, privacidad (el cuerpo no se persiste) |
| V. Simplicidad | ✅ sin colas: procesamiento en línea de un rango corto; el reintento de Beds24 + cron diario cubren fallos |

**Post-diseño (re-check)**: ✅ sin violaciones. Excepción menor a "write-only" (clave mostrada una vez al generarla) justificada en research R4.

## Project Structure

### Documentation (this feature)

```text
specs/020-beds24-webhooks/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/webhooks-api.md
└── checklists/requirements.md
```

### Source Code

```text
apps/api/
├── app/models/webhook.py                    # NUEVO: WebhookEvent
├── migrations/versions/a4b5c6d7e8f9_webhook_events.py
├── app/services/secret_service.py           # + "beds24_webhook_key" (kind "webhook")
├── app/services/webhook_service.py          # NUEVO: verificar clave, extraer pista, re-sync, bitácora, estado, generar clave
├── app/api/routes/hooks.py                  # NUEVO: POST /hooks/beds24, GET /hooks/beds24/status, POST /hooks/beds24/key
├── app/api/router.py                        # registra hooks
└── tests/test_webhooks.py

apps/web/
├── app/api/hooks/beds24/route.ts            # NUEVO: entrada pública → API privada (sin sesión, sin logs)
├── middleware.ts                            # /api/hooks/ público
├── app/(app)/settings/page.tsx              # tarjeta "Avisos en tiempo real" (estado + guía + generar clave)
└── lib/{types,api}.ts

docs/operations.md
```

## Decisiones clave (detalle en research.md)

1. **Versión 2 + Custom Header** `X-StayLever-Key: <clave>` (la cabecera no queda en URLs ni en logs de acceso).
2. **El aviso es una pista, Beds24 es la verdad**: se re-sincroniza `[min(arrival, check_in previo), max(departure, check_out previo)]` con `import_remote`; si faltan fechas, ventana por defecto hoy..+365.
3. **Respuestas**: 200 si se aceptó (incluso si el re-sync falló: queda `failed` y el cron corrige, evitando tormentas de reintentos); 401 sin clave/incorrecta; 503 si no hay clave configurada (la función está apagada). Aviso de otra propiedad → 200 `ignored`.
4. **Bitácora**: `webhook_event` sin cuerpo ni PII; se purgan eventos > 30 días al insertar.
5. **Clave**: generada por la app (`secrets.token_urlsafe(32)`), guardada cifrada como cualquier secreto y devuelta UNA vez como línea de cabecera lista para pegar.

## Complexity Tracking

Sin violaciones que justificar.
