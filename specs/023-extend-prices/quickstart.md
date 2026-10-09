# Quickstart: 023

```bash
cd apps/api && uv run pytest -q tests/test_price_extension_domain.py tests/test_price_extension.py
cd apps/web && npx tsc --noEmit && npm run lint && npm run build
```

1. Panel: aparece "Tienes precio solo hasta el 12 feb 2027 (4 meses)" con el botón "Extender precios".
2. Calendario → "Extender precios": plantilla feb 2027 … abr 2028 con un precio propuesto por mes, noches y aperturas.
3. Cambiar un mes, poner fin de semana +10 %, excluir un mes → la vista previa se recalcula; un precio < mínimo aparece "ajustado al mínimo".
4. Marcar "Entiendo…" y confirmar → resultado por mes.
5. Verificar en Beds24 / con una oferta: marzo de 2027 y marzo de 2028 tienen precio y están abiertas; las noches que ya tenían precio no cambiaron.
6. Calendario de marzo de 2027 (antes de extender): "sin precio", no $0, y la ocupación no las cuenta.
7. Revisar textos en en/pt.
