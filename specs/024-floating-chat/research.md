# Research: 024 Chat flotante

## R1 — Por qué hoy "se pierde" la conversación
`ChatPanel` guarda mensajes, `conversation_id` y propuesta en estado local; el servidor sí persiste `Message` (user/assistant/tool/system) y `AgentAction`. No hay endpoints de lectura de historial.

## R2 — Estado compartido
- **Decisión**: `ChatProvider` en `app/(app)/layout.tsx` (cliente) con `messages`, `conversationId`, `pendingActionId`, `busy`, `tool`, `send`, `newConversation`, `openConversation`, `reload`.
- **Alternativas**: dos instancias sincronizadas por eventos (duplica lógica); store global externo (dependencia nueva).

## R3 — Endpoints de historial
- `GET /chat/conversations?limit=20`: conversaciones con al menos un mensaje del host, ordenadas por el último mensaje; `title` = `Conversation.title` o primer mensaje del host (≤ 60, con "…"), `updated_at` = fecha del último mensaje, `message_count` (host + asistente).
- `GET /chat/conversations/{id}`: `messages` = solo `user`/`assistant` (rol `agent` para el asistente, igual que la UI), `pending_action_id` = última `AgentAction` `proposed`; 404 si no existe.

## R4 — UI del panel
- Botón fijo `bottom-5 right-5` (oculto en `/chat` y fuera del layout autenticado).
- Panel `fixed right-0 top-0 h-full` con ancho del estado (360–720, `localStorage`), asa de arrastre en el borde izquierdo; `< md` → `inset-0` (pantalla completa).
- Teclado: `keydown` global; `(e.metaKey||e.ctrlKey) && e.key==='k'` alterna; `Escape` cierra.
- Sin overlay oscuro: la página sigue visible y usable.

## R5 — Traducciones
Respuestas fijas del servidor guardadas en español → `trServer` también al pintar el historial (igual que en vivo).
