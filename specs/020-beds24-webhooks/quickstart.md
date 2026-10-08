# Quickstart: Reservas en tiempo real (020)

## Local

```bash
cd apps/api && uv run pytest -q tests/test_webhooks.py
cd apps/web && npm run build
```

## Puesta en marcha (host, una vez)

1. StayLever → Ajustes → **Avisos en tiempo real** → "Generar clave" → copiar la línea `X-StayLever-Key: …` (se muestra una sola vez).
2. Beds24 → Settings → Properties → Access → **Booking Webhook**: Version **2**, URL `https://staylever.com/api/hooks/beds24`, Custom Header = la línea copiada → Save.
3. Esperar el próximo cambio de reserva (o modificar/crear una de prueba) y ver en Ajustes "funcionando" con la hora del último aviso.

## Validación

1. **Sin clave** (antes del paso 1): `POST /api/hooks/beds24` → 503, sin cambios.
2. **Clave incorrecta**: 401, cuenta como rechazado, sin cambios.
3. **Aviso válido**: 200 `accepted`; la reserva/cancelación aparece en el calendario en ≤ 2 min; la bitácora registra el `sync_run`.
4. **Duplicado**: el mismo aviso dos veces → mismo estado, sin reservas duplicadas.
5. **Beds24 caído**: 200 `failed`; Ajustes lo muestra; el cron diario corrige.
6. **Privacidad**: los logs de `web` y `api` no contienen el nombre del huésped, la clave ni el cuerpo.
