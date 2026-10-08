# Quickstart: Selector de idioma (021)

## Local

```bash
cd apps/api && uv run pytest -q tests/test_preferences.py tests/test_agent_language.py tests/test_suggestion_v2_domain.py
cd apps/web && npx tsc --noEmit && npm run build   # falla si a en/pt les falta un texto
```

## Validación (demo local y luego producción)

1. Login: el selector aparece; con navegador en portugués abre en portugués la primera vez.
2. Elegir English → recorrer Dashboard, Calendario (mes y días en inglés), Chat, Sugerencias (bloques, vista previa, resultado), Ofertas, Conexión, Configuración (tarjetas, guías, secretos, avisos): ningún texto propio en español.
3. Precios en COP con formato del idioma; mismo valor.
4. Explicación de una sugerencia en pt: factores en portugués, nombre del evento intacto.
5. Error conocido (p. ej. vista previa obsoleta → 409) en inglés.
6. Chat en inglés: "¿precio del 20 de octubre?" → respuesta en inglés.
7. Cerrar sesión y entrar desde otro navegador: se mantiene el idioma (preferencia del servidor).
8. Celular: menú, selector y botones no se desbordan con textos largos.
