# ADR 0005 — Gestión de secretos desde la interfaz

**Fecha**: 2026-07-04 · **Estado**: aceptado · **Feature**: 017 (issue #99)

## Contexto

Los secretos operativos (OpenAI/Anthropic API key, Tavily, refresh token de Beds24) vivían solo
como variables de entorno en Railway: rotarlos exigía acceso a infraestructura y redeploy. El host
decidió (2026-07-03) hacerlos TODOS editables desde Configuración. La constitución exige: secretos
cifrados en reposo, nunca en el repositorio ni en logs.

## Decisión

1. **Cifrado**: Fernet (`cryptography`) con clave derivada del `SECRET_KEY` existente
   (`urlsafe_b64(sha256(secret_key))`). Fernet es cifrado AUTENTICADO: un valor cifrado con otra
   clave lanza `InvalidToken` de forma determinista → estado "ilegible" + fallback al entorno,
   sin romper el arranque. No se usa KDF lento: el SECRET_KEY ya es material aleatorio de alta
   entropía, no una contraseña humana.
2. **Precedencia**: valor guardado en la app (BD cifrada) > variable de entorno. Documentada y
   visible en la UI ("origen efectivo").
3. **Distribución**: caché en memoria del proceso, cargada en el lifespan de la API y al inicio
   de cada corrida del scan; write-through al guardar/quitar → rotación inmediata en la API sin
   redeploy. `get_secret(name)` es síncrono (los consumidores incluyen funciones sync).
4. **LiteLLM**: lee la key del ENTORNO del proceso → se pasa `api_key=` explícita por llamada
   (resuelta por proveedor); si no, una rotación guardada en BD jamás le llegaría.
5. **Write-only**: ninguna respuesta (estado, PUT, DELETE, auditoría, tests de servicio) contiene
   valores — ni en claro ni cifrados; solo pista de los últimos 4 (vacía si el valor es corto).
   Mensajes de error fijos. Test automatizado con valor centinela cubre todas las superficies.
6. **Auditoría**: `secret_change_log` append-only (secreto, acción, pista, fecha). Sin valores.
7. **Sin re-confirmación de contraseña**: el login de la web es la única puerta a la API privada;
   la pantalla es write-only y re-autenticar con la MISMA contraseña de la sesión no cambia el
   modelo de amenaza.
8. **Fuera de alcance**: SECRET_KEY, APP_PASSWORD y DATABASE_URL siguen en Railway (gestionarlos
   desde la app crearía dependencia circular); el agente de chat no tiene acceso a los secretos.

## Alternativas rechazadas

- AES-GCM manual (más superficie de error que Fernet), vault externo (YAGNI single-tenant),
  escribir `os.environ` al rotar (estado global implícito), consulta a BD por resolución
  (exigiría async en consumidores sync), reutilizar AgentAction para auditar (exige conversación).

## Consecuencias

- Rotar la clave del sistema (SECRET_KEY) deja lo guardado "ilegible" (estado honesto + fallback
  env); re-guardar repara. Documentado en operations.md.
- El proceso del scan adopta rotaciones en su corrida siguiente (aceptado; comunicado en la UI).
- Dependencia nueva: `cryptography`.
