# Contract: Preferencias y chat (021)

## GET /preferences (proxy con sesión)

200 → `{"language": "es"}`

## PUT /preferences (proxy con sesión)

Request `{"language": "en"}` → 200 `{"language": "en"}`. 422 `{"detail": "Idioma no soportado"}` si no es `es`/`en`/`pt`.

## POST /chat · /chat/stream (cambio aditivo)

Body gana `"language": "es" | "en" | "pt"` (opcional, default `"es"`). El asistente responde en ese idioma; herramientas, montos y confirmaciones no cambian.

## Factores de sugerencias (cambio aditivo en `rationale.factors[]`)

Ver data-model.md. Los consumidores existentes que leen `label`/`text` siguen funcionando.

## Web (sin API)

- Cookie `lang` = `es`|`en`|`pt`, `Path=/`, `Max-Age=31536000`, `SameSite=Lax`.
- `<html lang>` refleja el idioma activo.
