# Contrato: Feature 027

| Ruta | Respuesta |
|---|---|
| `POST /chat`, `POST /chat/stream` | + `quota: {used, limit, resets_on, warning}`; al límite (sin pendiente): respuesta normal con `limited: true` y el texto de límite, sin llamar a la IA |
| `GET /account/usage` | `{month, chat: {used, limit, resets_on}, search: {today, limit}, cost_usd}` |
| `GET /admin/usage?month=YYYY-MM` | `{month, accounts: [{id, name, status, chat_messages, llm_calls, input_tokens, output_tokens, searches, cost_usd, unpriced, chat_limit_month, search_limit_day}], total_cost_usd}` |
| `PATCH /admin/accounts/{id}/limits` | `{chat_limit_month?: int|null, search_limit_day?: int|null}` → límites vigentes |
