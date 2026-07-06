# Feature Specification: Gestión de secretos (API keys) desde la interfaz

**Feature Branch**: `017-secrets-ui`
**Created**: 2026-07-04
**Status**: Draft
**Input**: Issue #99 — Los secretos operativos (API key del LLM, búsqueda web, refresh token de Beds24) viven como variables de entorno en Railway; rotarlos exige entrar a otro dashboard y redeploy. Decisión del host (2026-07-03): TODOS editables desde Configuración, incluido el token de Beds24. La constitución exige secretos cifrados en reposo, nunca en el repositorio ni en logs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rotar un secreto desde Configuración (Priority: P1)

Como host, quiero reemplazar cualquiera de mis secretos operativos (OpenAI, Anthropic, Tavily, Beds24) desde la pantalla de Configuración, para rotar una credencial comprometida o renovada en segundos, sin tocar Railway ni esperar un redeploy.

**Why this priority**: es el objetivo del issue; hoy una rotación urgente (p. ej. key filtrada) depende de acceso a infraestructura.

**Independent Test**: guardar un valor nuevo para un secreto → el estado pasa a "guardado en la app" con la pista correcta, el servicio consumidor usa el valor nuevo de inmediato, y el valor completo no puede recuperarse por ninguna vía.

**Acceptance Scenarios**:

1. **Given** la sección Secretos de Configuración, **When** el host pega un valor nuevo y guarda, **Then** el estado muestra "guardado en la app" con la pista de los últimos 4 caracteres y el campo queda vacío (write-only).
2. **Given** un secreto guardado en la app, **When** cualquier servicio lo necesita (agente, scan, canal), **Then** usa el valor guardado — la rotación aplica de inmediato en la API (el proceso del scan diario la toma en su siguiente corrida, y la UI lo comunica).
3. **Given** un valor guardado, **When** el host lo QUITA, **Then** el sistema vuelve al valor de la variable de entorno (si existe) y el estado lo refleja ("por variable de entorno" o "sin configurar").
4. **Given** un valor vacío o solo espacios, **When** el host intenta guardar, **Then** el sistema lo rechaza con mensaje claro.
5. **Given** cualquier operación de esta pantalla, **When** se ejecuta, **Then** el valor completo NUNCA aparece: ni en la UI, ni en respuestas, ni en errores, ni en logs.

---

### User Story 2 - Ver el estado de los secretos sin exponerlos (Priority: P1)

Como host, quiero ver de un vistazo qué secretos están configurados y de dónde salen (guardado en la app vs variable de entorno), con solo la pista de los últimos 4 caracteres, para saber si algo falta o quedó viejo sin que la pantalla exponga nada sensible.

**Why this priority**: sin estado visible, la rotación es a ciegas; es la mitad de lectura del issue.

**Independent Test**: con un secreto por entorno, otro guardado en la app y otro ausente, la pantalla muestra los tres estados correctos, y ninguna respuesta contiene el valor.

**Acceptance Scenarios**:

1. **Given** un secreto presente solo como variable de entorno, **When** el host abre Secretos, **Then** ve "configurado · por variable de entorno" con su pista.
2. **Given** un secreto guardado en la app, **When** consulta, **Then** ve "configurado · guardado en la app" con su pista y cuándo se cambió por última vez.
3. **Given** un secreto ausente en ambos orígenes, **When** consulta, **Then** ve "sin configurar" y qué funcionalidad queda apagada (agente / scan / canal).
4. **Given** lo guardado quedó ilegible (la clave de cifrado del sistema cambió), **When** consulta, **Then** el estado lo dice honesto ("guardado ilegible — se usa la variable de entorno") y el sistema sigue funcionando con el fallback.

---

### User Story 3 - Probar cada servicio tras rotar (Priority: P2)

Como host, quiero un botón "Probar" por servicio (LLM, búsqueda, Beds24) que haga una verificación mínima con el secreto vigente, para confirmar que una rotación funcionó sin esperar a que algo falle en producción.

**Why this priority**: cierra el ciclo rotar → confirmar; sin él, un valor mal pegado se descubre cuando el agente o el scan fallan.

**Independent Test**: con credencial válida el test reporta éxito; con credencial inválida reporta fallo con motivo corto; en ningún caso la respuesta contiene el valor.

**Acceptance Scenarios**:

1. **Given** un secreto vigente válido, **When** el host pulsa "Probar", **Then** ve éxito con el detalle mínimo útil (p. ej. "conexión OK").
2. **Given** un secreto inválido/expirado, **When** prueba, **Then** ve el fallo con un motivo corto y honesto (p. ej. "credencial rechazada por el proveedor") SIN el valor ni fragmentos de él.
3. **Given** cualquier prueba, **When** se ejecuta, **Then** es solo lectura/ping: no cambia precios, disponibilidad ni configuración en ningún sistema.

---

### User Story 4 - Auditoría de cambios sin valores (Priority: P2)

Como host, quiero un registro de cuándo se guardó o quitó cada secreto (con su pista de 4 caracteres, nunca el valor), para poder reconstruir qué pasó si algo deja de funcionar tras una rotación.

**Why this priority**: exigencia del issue y de la constitución (auditoría de cambios); barato de construir junto al resto.

**Independent Test**: guardar y quitar un secreto genera dos entradas de auditoría con acción, fecha y pista; ninguna entrada contiene el valor.

**Acceptance Scenarios**:

1. **Given** el host guarda un secreto, **When** consulta la auditoría, **Then** hay una entrada con el nombre del secreto, acción "guardado", fecha y pista (…últimos 4).
2. **Given** el host quita un secreto, **When** consulta, **Then** hay una entrada "eliminado" con fecha.
3. **Given** cualquier entrada de auditoría, **When** se inspecciona (UI, BD o logs), **Then** no contiene el valor ni permite reconstruirlo.

---

### Edge Cases

- **Clave de cifrado del sistema rotada** (SECRET_KEY): lo guardado queda ilegible → el sistema NO rompe el arranque, cae a variables de entorno y el estado lo comunica; guardar de nuevo repara.
- **Secreto guardado y variable de entorno presentes a la vez**: gana lo guardado en la app (precedencia documentada); el estado muestra el origen efectivo.
- **Quitar un secreto sin variable de entorno de respaldo**: estado "sin configurar" + aviso de qué funcionalidad queda apagada; la app sigue arrancando (modo degradado honesto, como hoy sin keys).
- **Valor con espacios accidentales al pegar**: se recorta en los extremos antes de guardar.
- **Prueba con servicio externo caído** (credencial buena, proveedor caído): el resultado distingue en lo posible "credencial rechazada" de "servicio no disponible".
- **El agente de chat**: NO tiene herramienta para leer ni escribir secretos; solo la pantalla de Configuración.
- **Proceso del scan diario**: corre aparte; toma la rotación en su siguiente corrida (comunicado en la UI/docs).
- **Sin secretos guardados en BD**: comportamiento idéntico al actual (todo por entorno).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El host MUST poder guardar (reemplazar) y quitar el valor de cada secreto gestionable — API key de OpenAI, de Anthropic, de búsqueda (Tavily) y refresh token de Beds24 — desde Configuración, sin acceso a la infraestructura.
- **FR-002**: Los valores guardados MUST almacenarse cifrados en reposo; el mecanismo deriva de la clave de sistema existente y su elección exacta es decisión del plan.
- **FR-003**: La interfaz y la API MUST ser write-only para los valores: nunca se devuelve ni muestra un valor guardado; el estado expone solo configurado sí/no, origen, pista de últimos 4 caracteres y fecha del último cambio.
- **FR-004**: La precedencia MUST ser: valor guardado en la app > variable de entorno; documentada y reflejada en el estado ("origen efectivo").
- **FR-005**: Una rotación MUST aplicar de inmediato en el proceso de la API (siguientes peticiones usan el valor nuevo, sin redeploy); el proceso del scan la adopta en su siguiente corrida y la UI/documentación lo comunica.
- **FR-006**: Si lo guardado queda ilegible (clave de cifrado rotada), el sistema MUST arrancar y operar con el fallback de entorno y MUST comunicar el estado honesto; guardar de nuevo repara.
- **FR-007**: Cada guardado/eliminación MUST quedar auditada (secreto, acción, fecha, pista de 4) y la auditoría MUST NOT contener valores ni permitir reconstruirlos.
- **FR-008**: El host MUST poder probar cada servicio (LLM, búsqueda, Beds24) con su secreto vigente: verificación mínima de solo lectura, resultado honesto, sin exponer el valor ni fragmentos en éxito o error.
- **FR-009**: Los valores MUST NOT aparecer en logs, respuestas de error, el repositorio ni el historial del navegador (envío solo en cuerpos de petición autenticada).
- **FR-010**: El agente de chat MUST NOT tener acceso de lectura ni escritura a los secretos (sin herramientas nuevas).
- **FR-011**: Validación al guardar: valor no vacío tras recortar espacios; mensajes claros.
- **FR-012**: Sin valores guardados en la app, el comportamiento actual (todo por variables de entorno) MUST permanecer idéntico (los 210 tests existentes siguen verdes).

### Key Entities

- **Secreto gestionado (SecretEntry)** — NUEVA: nombre (de una lista cerrada de 4), valor cifrado, pista (últimos 4), fecha de cambio. Nunca sale de la API en claro.
- **Auditoría de secretos (SecretChangeLog)** — NUEVA: secreto, acción (guardado/eliminado), pista, fecha. Sin valores.
- **Estado de secretos (vista)**: derivada — por secreto: configurado, origen efectivo (app/entorno/ninguno), pista, último cambio, legibilidad.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host rota un secreto en menos de 60 segundos de punta a punta (pegar → guardar → probar OK) sin tocar Railway.
- **SC-002**: 0 apariciones del valor de un secreto en respuestas de la API, UI, auditoría o logs (verificable inspeccionando cada superficie tras guardar un valor centinela en pruebas).
- **SC-003**: Con un valor guardado, el 100% de las peticiones siguientes del servicio correspondiente usan el valor nuevo sin redeploy.
- **SC-004**: El 100% de los guardados/eliminaciones quedan auditados con pista y fecha.
- **SC-005**: Sin secretos guardados, los 210 tests existentes siguen verdes y el comportamiento es idéntico al actual.

## Assumptions

- Single-tenant: un solo host; el login de la web (única puerta a la API privada) es el control de acceso. **Decisión evaluada (pedida por el issue)**: NO se exige re-confirmación de contraseña en esta pantalla — la UI es write-only (no expone valores) y re-autenticar con la MISMA contraseña de la sesión no cambia el modelo de amenaza; queda documentado aquí.
- Secretos de infraestructura (SECRET_KEY, APP_PASSWORD, DATABASE_URL, SENTRY_DSN) quedan FUERA: se gestionan en Railway (gestionarlos desde la app crearía dependencia circular o superficie innecesaria).
- La "pista" son los últimos 4 caracteres — suficiente para distinguir valores sin habilitar reconstrucción.
- Probar el LLM puede consumir una fracción de centavo (petición mínima); aceptado por el host como costo de la verificación.
- La lista de secretos gestionables es cerrada (4); añadir proveedores nuevos (p. ej. AirDNA del #98) la extenderá en su propia feature.
- Fuera de alcance: multiusuario/roles, rotación del SECRET_KEY, integraciones nuevas.
