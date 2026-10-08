# Contract: Avisos de reservas (020)

## Público (web) — `POST https://staylever.com/api/hooks/beds24`

Configurado en Beds24 → Settings → Properties → Access → **Booking Webhook**:
- Webhook Version: **2**
- URL: `https://staylever.com/api/hooks/beds24`
- Custom Header: `X-StayLever-Key: <clave generada en Ajustes>`

Sin sesión. Cuerpo ≤ 256 KB (si no → 413). Reenvía cuerpo + `X-StayLever-Key` a la API privada y devuelve su estado. No registra nada.

## Privado (API) — `POST /hooks/beds24`

Request: cuerpo JSON de Beds24 V2 (`{timeStamp, booking{id, propertyId, arrival, departure, …}}`), cabecera `X-StayLever-Key`.

| Caso | HTTP | Cuerpo | Bitácora |
|---|---|---|---|
| Sin clave configurada | 503 | `{"detail": "Avisos no configurados"}` | — |
| Clave ausente o incorrecta | 401 | `{"detail": "No autorizado"}` | `rejected` |
| Propiedad distinta a la del host | 200 | `{"result": "ignored"}` | `ignored` |
| Aceptado y re-sincronizado | 200 | `{"result": "accepted"}` | `accepted` (+ `sync_run_id`) |
| Aceptado pero Beds24 falló al re-sincronizar | 200 | `{"result": "failed"}` | `failed` (detail fijo con tipo de error) |
| JSON inválido / sin `booking.id` | 200 | `{"result": "accepted"}` | re-sync con ventana por defecto (hoy..+90) |

Nota: ante 401/503 Beds24 reintenta (respuesta ≥ 400) hasta agotar sus intentos; los reintentos nunca cambian datos.

## Privado (API, vía proxy con sesión) — `GET /hooks/beds24/status`

```json
{
  "configured": true,
  "status": "active",
  "last_accepted_at": "2026-10-08T21:14:03Z",
  "counts_7d": {"accepted": 3, "ignored": 0, "rejected": 1, "failed": 0},
  "endpoint_url": "https://staylever.com/api/hooks/beds24",
  "header_name": "X-StayLever-Key"
}
```

`status`: `unconfigured` · `never` (clave sin avisos aún) · `active` · `idle` (último aceptado > 7 días).

## Privado (API, vía proxy con sesión) — `POST /hooks/beds24/key`

Genera y guarda una clave nueva (rota la anterior). **Única** respuesta que contiene el valor:

```json
{"header_line": "X-StayLever-Key: 3q2-…", "hint": "…a1B9"}
```

Después, `GET /settings/secrets` solo muestra la pista.
