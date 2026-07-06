# Contract: API de secretos (write-only) + pruebas por servicio

**Feature**: 017-secrets-ui · Tras el proxy con login (única puerta). **Ninguna respuesta contiene valores.**

## `GET /settings/secrets`

```json
{
  "secrets": [
    {
      "name": "openai_api_key",
      "label": "OpenAI API key",
      "service": "Agente de chat y extracción de eventos",
      "configured": true,
      "source": "env",
      "hint": "…Ab3d",
      "updated_at": null,
      "unreadable": false
    },
    {
      "name": "beds24_refresh_token",
      "label": "Beds24 refresh token",
      "service": "Todo el canal (precios, reservas, disponibilidad)",
      "configured": true,
      "source": "app",
      "hint": "…9xYz",
      "updated_at": "2026-07-04T10:00:00Z",
      "unreadable": false
    }
  ]
}
```

- `source`: "app" (BD, precede) | "env" (variable de entorno) | null (sin configurar).
- `unreadable: true` = guardado ilegible (clave de cifrado rotada) → se está usando el fallback env; guardar de nuevo repara.

## `PUT /settings/secrets/{name}`

Body: `{ "value": "sk-..." }` → 200 con el MISMO shape de estado del secreto (sin eco del valor).

- Recorta espacios en extremos; **422** si queda vacío; **404** si `name` no está en la lista cerrada.
- Efectos: cifra y guarda (upsert), actualiza caché (rotación inmediata), audita `set` con hint.

## `DELETE /settings/secrets/{name}`

→ 200 con el estado resultante (vuelve a `env` o `null`). 404 si el nombre no es válido o no hay valor guardado. Audita `deleted`.

## `POST /settings/secrets/{name}/test`

→ 200 `{ "ok": true, "detail": "conexión OK (1 propiedad)" }` o `{ "ok": false, "detail": "credencial rechazada por el proveedor" }`.

- Por servicio: LLM → completion mínima (max_tokens=1); búsqueda → 1 consulta; Beds24 → test de conexión existente. Solo lectura/ping.
- `detail` es SIEMPRE un mensaje fijo/categorizado; nunca interpola el valor ni excepciones crudas.

## `GET /settings/secrets/audit`

```json
{ "entries": [ { "name": "beds24_refresh_token", "action": "set", "hint": "…9xYz", "changed_at": "..." } ] }
```

## Web (contratos de UI)

- Tarjeta "Secretos" en Configuración: por secreto — label, servicio que apaga si falta, estado (configurado/origen/pista/último cambio/ilegible), campo password write-only + "Guardar", "Quitar" (solo si source=app), "Probar" con resultado inline; aviso fijo: "La rotación aplica de inmediato; el escaneo diario la toma en su próxima corrida".
- El campo se limpia tras guardar; nunca se rellena con el valor actual.

## Garantías transversales (SC-002)

- Ningún endpoint devuelve `value` ni `value_encrypted`; los errores usan mensajes fijos; la auditoría solo guarda hint; test automatizado con valor centinela verifica todas las superficies.
