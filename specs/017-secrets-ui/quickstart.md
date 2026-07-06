# Quickstart: verificar gestión de secretos

**Feature**: 017-secrets-ui

## Tests (sin APIs reales; cifrado real con SECRET_KEY de test)

```bash
cd apps/api && uv run pytest -q
cd apps/web && npm run build
```

Escenarios clave:
1. Cifrar/descifrar round-trip; `InvalidToken` (clave distinta) → unreadable + fallback env, sin excepción al arrancar.
2. Precedencia: BD > env > None; DELETE vuelve a env; caché write-through (get_secret refleja el PUT sin recargar).
3. Estado enmascarado: GET nunca contiene el valor; hint correcto; hint vacío si valor <8 chars.
4. **Centinela (SC-002)**: guardar "SENTINEL-XYZ-1234" → assert de que NO aparece en GET/PUT/DELETE/audit responses.
5. Validación: vacío/espacios → 422; nombre fuera de la lista → 404.
6. Auditoría: set y deleted con hint y sin valores.
7. Probar: dobles de LLM/search/Beds24 → ok y fallo categorizado; sin valores en detail.
8. FR-012: sin filas en BD, get_secret == settings.* para los 4 nombres.

## Verificación EN VIVO (con cuidado — el host pega los valores, yo NUNCA los veo)

```bash
WEB="https://web-production-dfcaf.up.railway.app"

# 1) GET estado: los 4 con source=env (Railway) y sus pistas.
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/settings/secrets" | python3 -m json.tool

# 2) EL HOST (no el agente) pega un valor en la UI — p. ej. rotar la key de Tavily
#    o re-guardar la actual: estado pasa a source=app, campo se limpia.
# 3) Botón "Probar" del servicio → OK.
# 4) Verificar que el servicio real sigue funcionando (p. ej. /status beds24=connected
#    si se rotó el token; el scan del día siguiente para search).
# 5) Auditoría: entrada "set" con pista, sin valor.
# 6) OPCIONAL reversible: "Quitar" el valor guardado → vuelve a env; probar de nuevo.
# ⚠️ El agente NUNCA maneja los valores: la semilla/rotación real la hace el host
#    pegándolos en la pantalla (Principio de la constitución: secretos nunca en logs
#    — incluidos los del chat de esta sesión).
```
