# Feature Specification: Selector de idioma (español, inglés, portugués)

**Feature Branch**: `021-language-selector`
**Created**: 2026-10-08
**Status**: Draft
**Input**: User description: "Selector de idioma: español, inglés y portugués (Feature 021, issue #124)."

## Contexto

StayLever está hoy solo en español. El host quiere poder usarla también en **inglés** y **portugués** (solo esos tres). El español sigue siendo el idioma de referencia: todo texto nuevo se escribe primero en español y luego se traduce.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cambiar el idioma de toda la app (Priority: P1)

Como host quiero elegir el idioma (Español, English, Português) desde un selector siempre visible y que **toda** la interfaz cambie al instante: menú, páginas, botones, diálogos, avisos y guías.

**Why this priority**: es el pedido completo; sin una interfaz totalmente traducida el selector no sirve.

**Independent Test**: elegir "English" en el selector y recorrer las 7 secciones (Dashboard, Calendario, Chat, Sugerencias, Ofertas, Conexión, Configuración), abrir una vista previa y provocar un aviso de éxito y uno de error: ningún texto propio de la app queda en español.

**Acceptance Scenarios**:

1. **Given** la app en español, **When** el host elige "English" en el selector, **Then** todos los textos propios de la app pasan a inglés sin recargar ni perder lo que estaba haciendo.
2. **Given** el idioma elegido, **When** el host cierra sesión, vuelve otro día o entra desde otro dispositivo, **Then** la app se abre en el idioma elegido.
3. **Given** la primera visita (sin preferencia guardada), **When** el navegador está en portugués, **Then** la app se muestra en portugués; si el navegador está en un idioma no soportado, se muestra en español.
4. **Given** la pantalla de inicio de sesión, **When** el host la abre, **Then** puede cambiar el idioma allí mismo.
5. **Given** cualquier diálogo (vista previa de precios, de disponibilidad, de sugerencias en lote, confirmaciones), **When** se abre en inglés o portugués, **Then** títulos, columnas, botones y motivos aparecen en ese idioma.

---

### User Story 2 - Fechas y números en el formato del idioma (Priority: P1)

Como host quiero que fechas, meses, días de la semana y números se muestren con el formato del idioma elegido, manteniendo los precios en pesos colombianos (COP).

**Why this priority**: una interfaz traducida con fechas en otro idioma se siente rota y puede confundir fechas.

**Independent Test**: en inglés, el calendario muestra "October 2026" y días "Mon, Tue…"; un precio se muestra con el formato numérico del idioma y con la moneda COP.

**Acceptance Scenarios**:

1. **Given** idioma inglés, **When** el host abre el calendario, **Then** el mes y los días de la semana están en inglés.
2. **Given** idioma portugués, **When** ve un rango "14–16 nov", **Then** ve el equivalente en portugués.
3. **Given** cualquier idioma, **When** ve un precio, **Then** está en COP con los separadores del idioma, sin convertir el valor.

---

### User Story 3 - Mensajes del sistema en el idioma elegido (Priority: P2)

Como host quiero que los mensajes que produce el sistema —errores, motivos por los que se omite una noche, la explicación de cada sugerencia, estados de conexión y de avisos— también aparezcan en el idioma elegido.

**Why this priority**: son textos frecuentes en los flujos de decisión (sugerencias, vistas previas); en otro idioma rompen la experiencia, pero la app es usable sin ellos.

**Independent Test**: en portugués, una vista previa de lote con una noche reservada muestra el motivo en portugués; la explicación de una sugerencia ("evento alto, +30%", "libre en 5 días", "mercado de la zona…") aparece en portugués conservando el nombre del evento tal cual.

**Acceptance Scenarios**:

1. **Given** idioma inglés, **When** una acción falla con un error conocido, **Then** el mensaje se muestra en inglés.
2. **Given** idioma portugués, **When** se muestra la explicación de una sugerencia, **Then** los factores (evento, ocupación, días libres, mercado) se leen en portugués y el nombre del evento se mantiene original.
3. **Given** un mensaje del sistema sin traducción disponible, **When** se muestra, **Then** aparece en español (nunca vacío ni como un código interno).

---

### User Story 4 - El asistente responde en mi idioma (Priority: P2)

Como host quiero que el asistente del chat me responda en el idioma elegido, aunque yo escriba en otro.

**Why this priority**: el chat es una vía principal de uso; contestar en otro idioma resulta incoherente.

**Independent Test**: con la app en inglés, preguntar "¿cuál es el precio del 20 de octubre?" y recibir la respuesta en inglés.

**Acceptance Scenarios**:

1. **Given** idioma inglés, **When** el host escribe al asistente, **Then** el asistente responde en inglés.
2. **Given** el host cambia el idioma, **When** envía el siguiente mensaje, **Then** el asistente responde en el idioma nuevo.
3. **Given** una propuesta del asistente que requiere confirmación, **When** se muestra, **Then** la confirmación (montos, fechas, botones) está en el idioma elegido; la acción y los montos son idénticos en cualquier idioma.

---

### User Story 5 - Corregir traducciones fácilmente (Priority: P3)

Como host quiero que, si encuentro una traducción que no me gusta, se pueda corregir de forma simple y que el texto en español siga siendo la referencia.

**Why this priority**: calidad a largo plazo; no bloquea el uso inicial.

**Independent Test**: todas las traducciones están reunidas en un solo lugar por idioma, con la misma lista de textos que el español; una verificación automática detecta textos faltantes en inglés o portugués.

**Acceptance Scenarios**:

1. **Given** un texto nuevo agregado en español, **When** falta su traducción, **Then** una verificación lo señala antes de publicar.
2. **Given** una corrección de traducción, **When** se publica, **Then** se ve en la app sin cambiar ningún comportamiento.

---

### Edge Cases

- Contenido del host o de terceros (nombres de eventos, notas del host, nombres de huéspedes, textos de Beds24, nombres de promociones): **nunca** se traduce.
- Textos muy largos en inglés o portugués (más largos que en español): no rompen botones, tarjetas ni el menú en celular.
- Cambiar de idioma en medio de una vista previa abierta: la vista previa sigue siendo válida (el cambio de idioma no altera montos ni la confirmación).
- Historial del chat: los mensajes anteriores quedan en el idioma en que se escribieron; solo los nuevos siguen el idioma actual.
- Registros de auditoría y datos guardados (motivos, explicaciones) no se reescriben: se muestran traducidos al leerlos.
- Navegador en "pt-PT" o "en-GB": se usa portugués o inglés respectivamente.

## Requirements *(mandatory)*

### Functional Requirements

**Selector y preferencia (US1)**

- **FR-001**: La app MUST ofrecer un selector con tres opciones —Español, English, Português—, cada una con su nombre en su propio idioma, accesible desde el menú lateral (escritorio y celular) y desde la pantalla de inicio de sesión.
- **FR-002**: Al elegir un idioma, todos los textos propios de la app MUST cambiar sin recargar la página ni perder el trabajo en curso.
- **FR-003**: La elección MUST recordarse para el host entre sesiones y dispositivos.
- **FR-004**: Sin preferencia guardada, la app MUST usar el idioma del navegador si es uno de los tres (cualquier variante regional) y español en otro caso.

**Cobertura de traducción (US1, US5)**

- **FR-005**: El 100 % de los textos propios de la interfaz (menú, 7 secciones, diálogos, avisos de éxito/error, guías, leyendas del calendario, estados, pantallas vacías, login) MUST estar disponible en los tres idiomas.
- **FR-006**: El contenido del host y de terceros MUST mostrarse sin traducir.
- **FR-007**: Las traducciones MUST estar reunidas por idioma con el español como referencia, y una verificación automática MUST fallar si a inglés o portugués le falta algún texto que exista en español.

**Formatos (US2)**

- **FR-008**: Fechas, nombres de meses y días, rangos de fechas y números MUST mostrarse con el formato del idioma elegido.
- **FR-009**: Los precios MUST seguir en COP, con el mismo valor en todos los idiomas.

**Mensajes del sistema (US3)**

- **FR-010**: Los mensajes que produce el sistema y ve el host (errores conocidos, motivos de omisión, factores de las sugerencias, estados de conexión y de avisos) MUST mostrarse en el idioma elegido.
- **FR-011**: Si un mensaje del sistema no tiene traducción, MUST mostrarse en español (nunca vacío ni como identificador interno).

**Asistente (US4)**

- **FR-012**: El asistente del chat MUST responder en el idioma elegido en el momento de cada mensaje.
- **FR-013**: Las confirmaciones del asistente MUST presentar los mismos montos, fechas y acciones en cualquier idioma.

**No regresión**

- **FR-014**: Cambiar de idioma MUST NOT alterar ningún comportamiento: cálculos, publicaciones al canal, confirmaciones y datos guardados son idénticos en los tres idiomas.

### Key Entities

- **Preferencia de idioma**: idioma elegido por el host (es, en, pt); se guarda una sola vez y aplica a todos sus dispositivos.
- **Catálogo de textos**: conjunto de textos de la interfaz por idioma, con el español como referencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con la app en inglés o portugués, 0 textos propios de la app visibles en español al recorrer las 7 secciones, los diálogos y el login.
- **SC-002**: Cambiar de idioma tarda menos de 1 segundo y no pierde datos escritos ni selecciones.
- **SC-003**: El idioma elegido se mantiene en el 100 % de los inicios de sesión posteriores, en cualquier dispositivo.
- **SC-004**: El asistente responde en el idioma elegido en ≥ 95 % de las respuestas.
- **SC-005**: La verificación de traducciones detecta el 100 % de los textos faltantes antes de publicar.
- **SC-006**: 0 diferencias de comportamiento (precios, publicaciones, confirmaciones) entre idiomas en las pruebas existentes.

## Assumptions

- **Portugués de Brasil** (pt-BR) e **inglés de EE. UU.** (en-US) como variantes; el navegador en pt-PT o en-GB usa esas mismas.
- Las traducciones iniciales las prepara el equipo con revisión del host; el host puede pedir correcciones después.
- La moneda se mantiene en COP en todos los idiomas (no hay conversión).
- Single-tenant: una sola preferencia de idioma (la del host).
- La documentación del repositorio, los registros técnicos y los textos que llegan de Beds24/OTAs quedan fuera de alcance.
- Los datos ya guardados (explicaciones de sugerencias, motivos) se traducen al mostrarse, sin migrar los datos existentes; si un dato antiguo solo existe como texto libre en español, se muestra en español.
