# Feature Specification: Frontend web (UX / dashboard)

**Feature Branch**: `006-web-frontend`  
**Created**: 2026-06-26  
**Status**: Draft  
**Input**: Interfaz web intuitiva que consume la API ya construida para que el host gestione precios y promociones de forma visual (calendario de precios, dashboard), revise sugerencias y converse con el agente; human-in-the-loop visible (preview + confirmación). Single-tenant, COP, Medellín, solo Booking.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver y gestionar precios en un calendario interactivo (Priority: P1)

El host abre un calendario mensual por unidad que muestra, por día, el precio efectivo y base, la disponibilidad y badges de promociones/eventos. Selecciona un día o arrastra para seleccionar un rango, propone un precio nuevo y ve una **previsualización (diff)** de qué días cambian; confirma para aplicar.

**Why this priority**: Es la tarea central del host y donde un buen UX marca la diferencia frente a la Extranet de Booking.

**Independent Test**: Abrir el calendario, seleccionar un rango, escribir un precio, ver el diff de los días afectados y confirmar; el calendario refleja los nuevos precios.

**Acceptance Scenarios**:

1. **Given** una unidad con precios, **When** el host abre el calendario de un mes, **Then** ve por día el precio efectivo/base, disponibilidad y promociones/eventos.
2. **Given** un rango seleccionado y un precio, **When** el host pide aplicar, **Then** ve primero una previsualización (días y valor anterior→nuevo) y nada se aplica sin confirmar.
3. **Given** una previsualización, **When** el host confirma, **Then** los precios se aplican y el calendario se actualiza.
4. **Given** un precio fuera de límites, **When** se previsualiza, **Then** esos días se señalan y no se aplican.

---

### User Story 2 - Conversar con el agente (chat) (Priority: P1)

El host abre el chat y escribe en lenguaje natural; ve la respuesta en streaming, el estado de las herramientas en ejecución, y cuando el agente propone un cambio, un resumen claro con botones **Confirmar / Cancelar**.

**Why this priority**: Es la cara "agéntica" del producto; el streaming y la confirmación visible hacen la experiencia confiable.

**Independent Test**: Pedir un cambio por chat, ver la propuesta con un botón de confirmar; confirmar y ver el resultado; "cancelar" no cambia nada.

**Acceptance Scenarios**:

1. **Given** el chat abierto, **When** el host pregunta un precio, **Then** la respuesta llega en streaming con datos reales.
2. **Given** una petición de cambio, **When** el agente responde, **Then** se muestra una propuesta con Confirmar/Cancelar y no se aplica nada hasta confirmar.
3. **Given** una propuesta, **When** el host confirma, **Then** la UI muestra el cambio aplicado.

---

### User Story 3 - Revisar y aplicar sugerencias (Priority: P2)

El host ve una bandeja de sugerencias ("qué te propongo") con justificación, confianza y día/rango, y puede aprobar, rechazar o aplicar cada una.

**Why this priority**: Conecta la inteligencia con la acción; valiosa pero secundaria al calendario y el chat.

**Independent Test**: Abrir la bandeja, ver una sugerencia con su justificación, aplicarla y ver el precio actualizado; rechazar otra y verla desaparecer de pendientes.

**Acceptance Scenarios**:

1. **Given** sugerencias pendientes, **When** el host abre la bandeja, **Then** ve cada una con justificación, confianza y día/rango.
2. **Given** una sugerencia, **When** el host la aplica, **Then** el precio se actualiza y la sugerencia pasa a "aplicada".
3. **Given** una sugerencia, **When** el host la rechaza, **Then** desaparece de pendientes sin cambiar precios.

---

### User Story 4 - Dashboard de panorama (Priority: P2)

El host ve un dashboard con KPIs de ocupación e ingresos, un heatmap del calendario de precios, próximos eventos relevantes y las sugerencias pendientes, con estados de carga y vacío claros.

**Why this priority**: Da contexto y dirección; no bloquea las acciones principales.

**Independent Test**: Abrir el dashboard y ver KPIs, heatmap, eventos y sugerencias; con datos vacíos, ver un estado vacío claro (no un error).

**Acceptance Scenarios**:

1. **Given** datos cargados, **When** el host abre el dashboard, **Then** ve ocupación, ingresos, heatmap, eventos y sugerencias pendientes.
2. **Given** sin datos, **When** se abre, **Then** se muestra un estado vacío claro y guías para empezar.

---

### User Story 5 - Onboarding y configuración (Priority: P2)

En el primer uso, un flujo guiado conecta el Channel Manager (Beds24), dispara la importación y selecciona la propiedad activa, mostrando el estado de sincronización. En Configuración, el host ajusta el LLM (proveedor, modelo general/acciones, presupuesto) y ve el estado de las integraciones, sin exponer secretos.

**Why this priority**: Necesario para arrancar y mantener, pero ocurre una vez / esporádicamente.

**Independent Test**: Completar el onboarding (conectar → importar → elegir propiedad) y ver el estado; cambiar el modelo de LLM en Configuración y verlo reflejado.

**Acceptance Scenarios**:

1. **Given** una cuenta nueva, **When** el host sigue el onboarding, **Then** conecta Beds24, importa y elige la propiedad activa, viendo el estado.
2. **Given** Configuración, **When** el host cambia el modelo de LLM, **Then** se guarda y se refleja; los secretos nunca se muestran.
3. **Given** una integración inválida (credenciales), **When** se abre Configuración, **Then** se indica el estado "inválido" con guía para corregir.

---

### User Story 6 - Notificaciones y responsive (Priority: P3)

El host recibe avisos (toasts / centro) cuando hay sugerencias nuevas o errores de sincronización, y puede usar la app cómodamente en el móvil.

**Why this priority**: Conveniencia y movilidad; mejora la experiencia sin bloquear.

**Independent Test**: Provocar un error de sync o una sugerencia nueva y ver el aviso; abrir la app en una pantalla estrecha y verificar que el calendario y el chat son usables.

**Acceptance Scenarios**:

1. **Given** una sugerencia nueva o un error de sync, **When** ocurre, **Then** el host ve un aviso claro.
2. **Given** una pantalla de móvil, **When** el host abre el calendario y el chat, **Then** son legibles y usables.

---

### Edge Cases

- **Backend no disponible / error de red**: la UI muestra un estado de error claro y permite reintentar; no se "rompe".
- **Previsualización obsoleta**: si el estado cambió entre previsualizar y confirmar, la UI vuelve a previsualizar en lugar de aplicar a ciegas.
- **Operación de rango con días inválidos**: se muestran señalados; se aplican solo los válidos.
- **Sin propiedad/datos aún**: estados vacíos con guías (no errores).
- **Streaming interrumpido en el chat**: la UI lo indica y permite reintentar; no deja un mensaje a medias sin contexto.
- **Acción de escritura sin confirmar**: nunca se envía; el botón de confirmar es explícito.
- **Carga lenta**: estados de carga (skeletons) en lugar de pantallas en blanco.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La UI MUST ofrecer un sistema de diseño consistente (tema, modo claro/oscuro, componentes base reutilizables) priorizando claridad y facilidad de uso.
- **FR-002**: La UI MUST mostrar un calendario de precios mensual por unidad con, por día, el precio efectivo y base, la disponibilidad y badges de promociones/eventos (heatmap).
- **FR-003**: La UI MUST permitir seleccionar un día o un rango (incluido arrastrar) y proponer un precio.
- **FR-004**: Toda escritura de precio MUST mostrar una previsualización (días afectados, valor anterior→nuevo) y aplicarse SOLO tras una confirmación explícita; los días inválidos se señalan y se excluyen.
- **FR-005**: Si el estado cambió entre la previsualización y la confirmación, la UI MUST re-previsualizar en vez de aplicar.
- **FR-006**: La UI MUST ofrecer un chat con respuesta en streaming, estado de herramientas en ejecución, y para las propuestas del agente botones claros de Confirmar/Cancelar.
- **FR-007**: La UI MUST mostrar una bandeja de sugerencias con justificación, confianza y día/rango, y permitir aprobar/rechazar/aplicar.
- **FR-008**: La UI MUST ofrecer un dashboard con KPIs de ocupación e ingresos, heatmap, eventos próximos y sugerencias pendientes, con estados de carga y vacío.
- **FR-009**: La UI MUST ofrecer un onboarding guiado para conectar el Channel Manager, importar y seleccionar la propiedad activa, mostrando el estado de sincronización.
- **FR-010**: La UI MUST ofrecer Configuración del LLM (proveedor, modelo general/acciones, presupuesto) y estado de integraciones, sin exponer secretos.
- **FR-011**: La UI MUST notificar (avisos) sugerencias nuevas y errores de sincronización.
- **FR-012**: La UI MUST ser responsive (usable en móvil) para el calendario y el chat.
- **FR-013**: La UI MUST manejar errores de backend/red con estados claros y opción de reintentar; nunca aplica una escritura sin confirmación.
- **FR-014**: La UI MUST consumir la API existente y NO reimplementar lógica de negocio (precios, sugerencias, auditoría viven en el backend).
- **FR-015**: La UI MUST limitar el acceso con una autenticación simple del host (single-tenant), sin gestión multiusuario.

### Key Entities *(include if feature involves data)*

La UI no posee datos propios de dominio; consume los del backend (propiedades/unidades, calendario/precios, promociones, sugerencias, eventos, conversaciones, estado de conexión). Conceptos de UI:

- **Vista de calendario (CalendarView)**: estado de la vista (mes, unidad seleccionada, selección de días/rango).
- **Borrador de cambio (ChangeDraft)**: precio propuesto + previsualización recibida + huella, antes de confirmar.
- **Sesión del host (HostSession)**: estado de autenticación simple y propiedad activa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host puede cambiar el precio de un fin de semana completo en menos de 1 minuto desde el calendario (seleccionar → previsualizar → confirmar).
- **SC-002**: Ninguna escritura de precio se aplica sin una previsualización y una confirmación visibles (0% de cambios a ciegas).
- **SC-003**: El host entiende el panorama (ocupación, ingresos, sugerencias) de un vistazo desde el dashboard.
- **SC-004**: La respuesta del chat empieza a mostrarse en streaming en pocos segundos y las propuestas siempre ofrecen Confirmar/Cancelar.
- **SC-005**: El calendario y el chat son usables en una pantalla de móvil (sin scroll horizontal roto ni controles inaccesibles).
- **SC-006**: Ante un error de backend, la UI muestra un estado claro y permite reintentar (no pantallas en blanco ni cuelgues).
- **SC-007**: Ningún secreto (API keys) se muestra en la interfaz.

## Assumptions

- **Consume la API existente** (FastAPI): `/sync`, `/pricing` (calendar/preview/apply/rollback/promotions/history), `/chat` (+ SSE `/chat/stream`), `/suggestions`. No duplica lógica de negocio.
- **Single-tenant, COP, Medellín, solo Booking**; autenticación simple del host.
- **Sistema de diseño** sobre la base ya existente en `apps/web` (Tailwind + shadcn/ui).
- **Human-in-the-loop visible**: preview + confirmación en toda escritura; el calendario/cambios reutilizan el flujo de preview/apply del backend.
- **Fuera de alcance**: cambios en el backend, despliegue (Fase 7), y gestión activa de otros canales (Airbnb).
- **Verificación**: la build de producción compila sin errores de tipos/lint; los flujos clave (calendario→preview→confirmar, chat→propuesta→confirmar, sugerencias) son demostrables contra el backend (o datos simulados).
