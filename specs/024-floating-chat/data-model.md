# Data Model: 024

Sin cambios de esquema.

## Vistas
- `ConversationSummary {id, title, updated_at, message_count}`
- `ConversationDetail {id, title, messages: [{role: "user"|"agent", text, created_at}], pending_action_id: int|null}`

## Estado del navegador
- `staylever.chat.conversation` → id de la conversación en curso.
- `staylever.chat.width` → ancho del panel (360–720).
