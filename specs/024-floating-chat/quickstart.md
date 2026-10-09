# Quickstart: 024

```bash
cd apps/api && uv run pytest -q tests/test_chat_history.py
cd apps/web && npx tsc --noEmit && npm run lint && npm run build
```

1. Calendario → botón flotante (abajo a la derecha) → panel a la derecha con el calendario visible.
2. Preguntar algo; pedir un cambio → Confirmar/Cancelar; confirmar → el calendario de fondo se actualiza.
3. Ir a Chat → misma conversación; recargar → sigue (y la propuesta pendiente también).
4. Ctrl+K / ⌘K abre/cierra; Esc cierra; arrastrar el borde cambia el ancho y se recuerda.
5. "Nueva conversación" y "Recientes" → retomar una anterior.
6. Celular (375 px) → pantalla completa. Textos en en/pt.
