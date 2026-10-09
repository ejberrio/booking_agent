# Implementation Plan: Chat flotante accesible desde cualquier pantalla

**Branch**: `024-floating-chat` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/024-floating-chat/spec.md` · issue #127

## Summary

La conversación pasa de estado local del componente a un **ChatProvider** (contexto React) montado en el layout autenticado, compartido por la sección Chat y un nuevo **panel flotante**. El id de la conversación en curso se recuerda en el navegador y los mensajes se recuperan del servidor con dos endpoints de solo lectura nuevos: lista de conversaciones recientes y detalle de una conversación (mensajes visibles + propuesta pendiente). El panel flotante (botón abajo a la derecha, Ctrl+K/⌘K, Esc, ancho ajustable, pantalla completa en celular) reutiliza el mismo `ChatPanel`. Cuando una respuesta aplica un cambio, se invalidan las consultas para que la pantalla de fondo se actualice.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: existentes (React Query, lucide-react, sonner); SIN dependencias nuevas
**Storage**: sin migraciones; usa `conversation`, `message`, `agent_action` existentes. El título se deriva del primer mensaje del host al listar.
**Testing**: pytest de los endpoints nuevos; web tsc/eslint/build + demo local (panel en calendario, continuidad con Chat, recarga con propuesta pendiente, historial, es/en)
**Target Platform**: Railway
**Project Type**: monorepo web application
**Constraints**: mismas capacidades que el chat actual (mismo `/chat/stream`); Principio III intacto (las propuestas siguen confirmándose); es/en/pt; no romper 341 tests
**Scale/Scope**: 1 ruta API ampliada + ~5 archivos web

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo |
| II. Provider-agnostic | ✅ no toca canales |
| III. Human-in-the-loop | ✅ el panel usa el mismo flujo de propuesta + Confirmar; recuperar una propuesta tras recargar no la aplica |
| IV. Tipado y pruebas | ✅ endpoints con tests; tipos TS |
| V. Simplicidad | ✅ sin tablas nuevas, sin dependencias; un solo componente de chat reutilizado |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

```text
specs/024-floating-chat/ (spec, plan, research, data-model, quickstart, contracts/chat-history-api.md, tasks)

apps/api/
├── app/api/routes/chat.py            # GET /chat/conversations, GET /chat/conversations/{id}
└── tests/test_chat_history.py        # NUEVO

apps/web/
├── lib/chat-store.tsx                # NUEVO: ChatProvider + useChat (conversación compartida, persistencia, send)
├── components/chat/chat-panel.tsx    # usa useChat; cabecera con "Nueva" y "Recientes"
├── components/chat/floating-chat.tsx # NUEVO: botón flotante + panel lateral (Esc, Ctrl/⌘K, ancho ajustable, móvil)
├── app/(app)/layout.tsx              # monta ChatProvider + FloatingChat
├── lib/{api,types}.ts · lib/i18n/catalog/chat.ts (es/en/pt)
docs/operations.md                    # sección Feature 024
```

## Decisiones clave (detalle en research.md)

1. **Estado compartido = contexto en el layout** (no un segundo chat): Chat y panel muestran exactamente lo mismo.
2. **Persistencia**: `localStorage["staylever.chat.conversation"]` = id; mensajes del servidor (`GET /chat/conversations/{id}`); al volver a enfocar la pestaña se recarga si no está enviando.
3. **Título**: primer mensaje del host recortado a 60 (sin migración).
4. **Propuesta pendiente**: el detalle devuelve `pending_action_id` (última `AgentAction` `proposed` de la conversación) → reaparecen Confirmar/Cancelar.
5. **Refresco de fondo**: si `done.applied` → `queryClient.invalidateQueries()`.
6. **Atajo**: Ctrl+K / ⌘K alterna; Esc cierra; ancho 360–720 px recordado.

## Complexity Tracking

Sin violaciones.
