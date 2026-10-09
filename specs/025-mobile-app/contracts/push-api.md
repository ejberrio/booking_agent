# Contract: 025

## POST /push/devices
Body `{"token": "...", "platform": "android", "model": "Pixel 8", "app_version": "1.0.0"}` → upsert por token (reactiva si estaba desactivado) → `{"id": 3, "notify_bookings": true, "notify_suggestions": true, "enabled": true}`

## GET /push/devices
`[{"id", "platform", "model", "app_version", "notify_bookings", "notify_suggestions", "enabled", "last_seen_at", "last_error"}]` (sin token)

## PATCH /push/devices/{id}
`{"notify_bookings"?: bool, "notify_suggestions"?: bool}` → dispositivo actualizado; 404.

## DELETE /push/devices/{id} → `{"deleted": true}`; 404.

## POST /push/test → `{"sent": 2, "failed": 0, "configured": true}`; si no hay credenciales: `{"sent": 0, "failed": 0, "configured": false}`.

## GET /push/status → `{"configured": true, "devices": 2}`

## Datos del aviso (FCM `data`)
`{"url": "/calendar?month=2026-11"}` · `{"url": "/suggestions"}`

## Web
- `/api/login`: User-Agent con `StayLeverApp/` → cookie y token de 90 días.
- `/calendar?month=YYYY-MM` abre ese mes.
