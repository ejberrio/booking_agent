# Contract: 024

## GET /chat/conversations?limit=20
`[{"id": 12, "title": "¿Cuánto cobro el 14 de noviembre?", "updated_at": "2026-10-09T15:20:00Z", "message_count": 6}]`
Solo conversaciones con ≥ 1 mensaje del host; orden por último mensaje desc; `limit` 1..50 (default 20).

## GET /chat/conversations/{id}
`{"id": 12, "title": "...", "messages": [{"role": "user"|"agent", "text": "...", "created_at": "..."}], "pending_action_id": 7 | null}`
404 si no existe. Nunca incluye mensajes `system`/`tool`.
