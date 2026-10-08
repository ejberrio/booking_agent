# Quickstart: 022

```bash
cd apps/api && uv run pytest -q tests/test_promo_floor.py tests/test_suggestion_promotions.py
cd apps/web && npx tsc --noEmit && npm run build
```

1. Ajustes → Precio mínimo por noche = 230.000.
2. Sugerencias: marcar un bloque a la baja y uno al alza → Previsualizar: la bajada muestra "promoción", % y precio desde el celular por canal; la subida "precio base".
3. Confirmar → la subida cambia el base; la bajada aparece en Ofertas como "StayLever · …" con marca "desde sugerencias"; el base de esas noches no cambió.
4. Recorte: con mínimo alto, la vista previa dice "recortado por el precio mínimo" u omite la noche.
5. Promoción pasada → "finalizada" en Ofertas.
6. Revisar textos en en/pt.
