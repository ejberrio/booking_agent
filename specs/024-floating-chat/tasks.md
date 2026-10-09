# Tasks: Chat flotante accesible desde cualquier pantalla

**Input**: `/specs/024-floating-chat/`
**Tests**: incluidos para los endpoints nuevos.

## Phase 1: Foundational (API de historial)

- [X] T001 `apps/api/app/api/routes/chat.py`: `GET /chat/conversations` (limit 1..50, solo con mensajes del host, orden por último mensaje, título derivado ≤ 60) y `GET /chat/conversations/{id}` (solo user/assistant → `user`/`agent`, `pending_action_id` = última `AgentAction` `proposed`, 404)
- [X] T002 [P] Tests `apps/api/tests/test_chat_history.py`: filtra system/tool; título recortado; orden y límite; conversación sin mensajes del host no aparece; pending_action_id presente/ausente (applied/cancelled no cuentan); 404

## Phase 2: US2 — Conversación compartida y persistente (P1)

- [X] T003 [US2] `apps/web/lib/api.ts` + `lib/types.ts`: `listConversations`, `getConversation`
- [X] T004 [US2] `apps/web/lib/chat-store.tsx`: `ChatProvider`/`useChat` (estado compartido; id en `localStorage`; carga al montar; recarga al enfocar si no está enviando; conversación inexistente → nueva; `send` vía `streamChat`; `applied` → `invalidateQueries`; `newConversation`, `openConversation`)
- [X] T005 [US2] `apps/web/components/chat/chat-panel.tsx`: usar `useChat`; cabecera con "Nueva conversación" y "Recientes" (lista con título y fecha); prop `compact` para el panel; historial traducido con `trServer`

## Phase 3: US1 — Panel flotante (P1)

- [X] T006 [US1] `apps/web/components/chat/floating-chat.tsx`: botón flotante (oculto en `/chat`), panel lateral superpuesto sin overlay, asa para ancho 360–720 recordado, pantalla completa `< md`, Esc / Ctrl+K / ⌘K, botón cerrar, `aria-*`
- [X] T007 [US1] `apps/web/app/(app)/layout.tsx`: montar `ChatProvider` + `FloatingChat`; `app/(app)/chat/page.tsx` sigue usando `ChatPanel`
- [X] T008 [P] [US1] Textos es/en/pt en `apps/web/lib/i18n/catalog/chat.ts` (abrir/cerrar asistente, nueva conversación, recientes, sin conversaciones, atajo)

## Phase 4: US3 — Recientes (P2)

- [X] T009 [US3] Lista "Recientes" en `chat-panel.tsx` (hasta 20, título + fecha relativa/corta, marca la actual) → `openConversation`

## Phase 5: Polish

- [X] T010 `docs/operations.md`: sección "Chat flotante (Feature 024)"
- [X] T011 Validación: ruff + pytest; tsc + eslint + build; demo local (panel en Calendario, continuidad con Chat, recarga con propuesta pendiente, Recientes, Ctrl+K/Esc, móvil 375 px, en)

## Dependencies
T001 → T002, T003 → T004 → T005 → T006 → T007; T008 [P]; T009 tras T005. Polish al final.
