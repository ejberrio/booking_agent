# Feature Specification: Extender precios hacia el futuro

**Feature Branch**: `023-extend-prices`
**Created**: 2026-10-08
**Status**: Draft
**Input**: User description: "Extender los precios más allá de mayo de 2027 (issue #126)."

## Contexto

El apartamento solo puede reservarse mientras cada noche tenga **precio** y esté **abierta** en el Channel Manager. Al revisar Beds24 (2026-10-08) se encontró que la situación es más urgente de lo que decía el aviso de Beds24 ("No price after 3 May 2027"):

- Hay precio solo hasta el **12 de febrero de 2027**. Desde el 13 de febrero las noches **no tienen precio y están cerradas** (0 disponibles); el 1–3 de mayo están abiertas pero sin precio.
- Pedir una oferta a Beds24 para marzo, mayo o junio de 2027 no devuelve nada: hoy el apartamento **no se puede reservar** después del 12 de febrero de 2027 (≈ 4 meses).
- Beds24 **no devuelve precios pasados**, y la app solo conoce precios desde junio de 2026; no hay "mismo día del año anterior" para febrero–junio.
- La app guarda esas noches sin precio como precio **0**, y por eso el calendario y los indicadores las tratan como si tuvieran precio u ocupación.

Decisiones del host (2026-10-08):
1. **Regla**: plantilla **mensual editable**. La app propone un precio por mes a partir de los precios ya cargados (sin los picos de eventos) y el host lo ajusta en la vista previa. Opcionalmente, un % extra para viernes y sábado. Después, las sugerencias ajustan noches puntuales.
2. **Horizonte**: **18 meses** desde hoy por defecto.
3. **Disponibilidad**: las noches sin precio y cerradas **se abren** al cargarles precio. Las noches que el host bloqueó desde la app no se abren. En la vista previa el host puede excluir meses.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extender precios con vista previa y confirmación (Priority: P1)

Como host, quiero cargar precio (y abrir) todas las noches futuras sin precio hasta 18 meses desde hoy con una plantilla mensual que reviso y ajusto, para que el apartamento se pueda reservar con anticipación en Booking.com y Airbnb.

**Why this priority**: sin esto, desde el 13 de febrero de 2027 no entran reservas.

**Independent Test**: abrir "Extender precios", ver la plantilla propuesta (feb 2027 … abr 2028), cambiar el precio de un mes, previsualizar (noches por mes, entre semana / fin de semana, noches que se abren), confirmar: Beds24 muestra precio en esas noches y una oferta para marzo de 2027 devuelve precio.

**Acceptance Scenarios**:

1. **Given** noches futuras sin precio dentro del horizonte, **When** el host abre "Extender precios", **Then** ve una fila por mes con el precio propuesto, cuántas noches recibirán precio y cuántas se abrirán.
2. **Given** la plantilla, **When** el host cambia el precio de un mes, el % de fin de semana, la fecha final o excluye un mes, **Then** la vista previa se recalcula antes de confirmar.
3. **Given** una vista previa, **When** el host confirma, **Then** cada noche incluida recibe su precio en el Channel Manager (y en la app, con auditoría), y las noches cerradas sin precio se abren.
4. **Given** noches que **ya tienen precio**, **When** se extiende, **Then** no se tocan (ni precio ni disponibilidad).
5. **Given** noches que el host **bloqueó desde la app**, **When** se extiende, **Then** reciben precio pero siguen cerradas, y la vista previa lo indica.
6. **Given** noches con **reserva confirmada**, **When** se extiende, **Then** se omiten.
7. **Given** que algo cambió entre la vista previa y la confirmación (por ejemplo, otra escritura cargó precio en una noche), **When** el host confirma, **Then** la confirmación se rechaza como obsoleta y se pide previsualizar de nuevo.
8. **Given** que la publicación de un mes falla, **When** termina, **Then** el resultado lo dice por mes; ese mes no queda con precio en la app y los demás meses sí se aplican.

---

### User Story 2 - Precio dentro de los límites del host (Priority: P1)

Como host, quiero que ningún precio extendido quede por debajo de mi precio mínimo (ni por encima del máximo, si lo hay).

**Why this priority**: es dinero; un precio mal propuesto se vendería sin revisión noche a noche.

**Independent Test**: con mínimo $230.000, un mes con plantilla de $200.000 aparece en la vista previa como $230.000 con la marca "ajustado al mínimo".

**Acceptance Scenarios**:

1. **Given** un precio de plantilla (o con el % de fin de semana) por debajo del mínimo, **When** se previsualiza, **Then** se usa el mínimo y se marca "ajustado al mínimo".
2. **Given** un máximo configurado y un precio por encima, **When** se previsualiza, **Then** se usa el máximo y se marca "ajustado al máximo".
3. **Given** un precio de plantilla de 0 o negativo, **When** se previsualiza, **Then** la API lo rechaza.

---

### User Story 3 - Aviso cuando quedan pocos meses con precio (Priority: P2)

Como host, quiero que la app me avise cuando quedan **menos de 12 meses** con precio, con acceso directo para extender, sin depender del aviso de Beds24.

**Why this priority**: evita llegar otra vez a esta situación; la extensión funciona sin el aviso.

**Independent Test**: con precios hasta el 12 de febrero de 2027, el panel y el calendario muestran "Tienes precio solo hasta el 12 feb 2027 (4 meses). Extender precios".

**Acceptance Scenarios**:

1. **Given** que la primera noche futura sin precio está a menos de 12 meses, **When** el host abre el panel o el calendario, **Then** ve el aviso con la fecha y un botón "Extender precios".
2. **Given** 12 meses o más con precio, **When** abre el panel, **Then** no hay aviso.
3. **Given** el aviso en el panel, **When** pulsa "Extender precios", **Then** llega al calendario con el diálogo abierto.

---

### User Story 4 - Las noches sin precio dejan de verse como "precio 0" (Priority: P2)

Como host, quiero que el calendario y los indicadores muestren "sin precio" en las noches que no tienen precio, en vez de $0 u ocupadas.

**Why this priority**: hoy confunde y distorsiona la ocupación del mes; es corrección de datos.

**Independent Test**: en marzo de 2027 (antes de extender), el calendario muestra las noches sin precio y la ocupación del mes no las cuenta como ocupadas.

**Acceptance Scenarios**:

1. **Given** una noche sin precio en el Channel Manager, **When** la app sincroniza, **Then** no guarda un precio 0.
2. **Given** precios 0 ya guardados, **When** se despliega la feature, **Then** se tratan como "sin precio".
3. **Given** una noche sin precio, **When** el motor de sugerencias corre, **Then** no la sugiere.

### Edge Cases

- Horizonte por encima de 24 meses desde hoy → rechazado.
- Fecha final anterior a la primera noche sin precio → nada que extender; la vista previa lo dice.
- Mes sin noches objetivo (todas con precio) → no aparece en la plantilla.
- Un mes con todas sus noches excluidas → no se publica nada de ese mes.
- Noches pasadas → nunca se tocan.
- Sin conexión al Channel Manager durante la vista previa → error claro; no se puede confirmar.
- Mismo mes en dos años distintos (por ejemplo, feb 2027 y feb 2028) → son filas separadas y cada una se puede editar.
- Una escritura publicada en Beds24 cuya verificación falla → ese mes queda como fallido en la app. La siguiente vista previa lee Beds24 y ya no lo propone si quedó con precio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST identificar las noches objetivo: desde hoy hasta la fecha final elegida (por defecto hoy + 18 meses, máximo hoy + 24 meses), sin precio en el Channel Manager y sin reserva confirmada.
- **FR-002**: El sistema MUST proponer una **plantilla por mes** (año-mes) para los meses con noches objetivo. Para cada mes usa la **mediana** de los precios conocidos de ese mismo mes del año, sin las noches con evento. Si no hay datos de ese mes, usa la mediana de todos los precios conocidos sin evento. El resultado se redondea a miles de COP.
- **FR-003**: El host MUST poder editar el precio de cada mes, excluir meses, fijar un % adicional para viernes y sábado (0–50 %, por defecto 0) y cambiar la fecha final antes de confirmar.
- **FR-004**: El precio final de cada noche (plantilla + % de fin de semana) MUST quedar dentro de [mínimo, máximo] de la regla de precios activa, marcando la noche como ajustada cuando corresponda.
- **FR-005**: La vista previa MUST mostrar por mes: noches objetivo, precio entre semana y de fin de semana, noches que se abrirán, noches que seguirán cerradas por bloqueo del host, noches ajustadas al mínimo o al máximo, y los totales. MUST incluir una huella del estado leído.
- **FR-006**: La confirmación MUST exigir la huella de la vista previa; si el estado cambió, MUST rechazarse como obsoleta, sin escribir nada.
- **FR-007**: Al confirmar, el sistema MUST fijar el precio en la app (con auditoría de origen "extensión") y publicarlo en el Channel Manager. Las noches cerradas sin precio que el host no bloqueó desde la app MUST abrirse (con auditoría de disponibilidad) en la misma escritura.
- **FR-008**: Las noches con precio previo MUST quedar intactas (precio y disponibilidad); las bloqueadas por el host desde la app MUST recibir precio pero seguir cerradas; las que tienen reserva confirmada MUST omitirse.
- **FR-009**: La publicación MUST hacerse por **mes**: si un mes falla, sus cambios locales se deshacen, se registra una incidencia de sincronización y los demás meses siguen.
- **FR-010**: El sistema MUST exponer el estado del horizonte: primera noche futura sin precio, meses cubiertos y si hace falta extender (< 12 meses).
- **FR-011**: El panel y el calendario MUST mostrar el aviso de FR-010 con acceso directo al diálogo de extensión.
- **FR-012**: La sincronización entrante MUST dejar de guardar precio 0 para noches sin precio. Los precios ≤ 0 ya guardados MUST tratarse como "sin precio" en el calendario, los indicadores y el motor de sugerencias.
- **FR-013**: Todos los textos nuevos MUST existir en español, inglés (EE. UU.) y portugués (Brasil).
- **FR-014**: Requiere confirmación reforzada: el host marca "Entiendo que se publicarán N noches en Booking.com y Airbnb" antes de confirmar.

### Key Entities

- **Plantilla de extensión** (no persistida): fecha final, % de fin de semana, abrir noches cerradas (sí/no), y por año-mes: precio e incluido.
- **Noche objetivo**: fecha, precio resultante, ajustada (mínimo/máximo), acción de disponibilidad (abrir / seguir cerrada / sin cambio).
- **Estado del horizonte**: primera noche sin precio, meses cubiertos, necesita extender.

## Success Criteria *(mandatory)*

- **SC-001**: Tras extender, una oferta de Beds24 para cualquier noche libre incluida dentro del horizonte devuelve precio (verificable para marzo de 2027 y marzo de 2028).
- **SC-002**: El host extiende 18 meses con una sola vista previa y una confirmación, en menos de 2 minutos.
- **SC-003**: 0 noches con precio previo modificadas; 0 noches reservadas o bloqueadas por el host abiertas.
- **SC-004**: 0 noches extendidas por debajo del mínimo configurado.
- **SC-005**: Con menos de 12 meses con precio, el aviso aparece en el panel y en el calendario.

## Assumptions

- La disponibilidad abierta es `units_count` de la unidad (1 hoy).
- "Fin de semana" = noches de viernes y sábado.
- Booking.com y Airbnb reciben de Beds24 lo que su ventana de reservas acepte; la app no controla esa ventana.
- El aviso usa los datos locales, que la sincronización diaria mantiene al día para 365 días.
- Fuera de alcance: cambiar precios ya cargados, extensión automática sin confirmación, extensión desde el chat del agente.

## Addendum (2026-10-09): aperturas que el Channel Manager no aplica

En producción Beds24 aceptó (`success`) abrir las noches desde el 13-feb-2027 pero el inventario siguió en 0 (ticket Beds24 #1064511). Pedido del host: la app debe comprobar si las fechas quedaron abiertas y avisar claramente cuando no.

- **FR-015**: Tras extender, el sistema MUST releer el CM y contar las noches que se pidió abrir y siguen cerradas; el resultado MUST mostrarlas en un aviso destacado (total y por mes) y la app MUST guardar la disponibilidad real (no la pedida).
- **FR-016**: La vista previa MUST avisar cuántas noches ya tienen precio pero están cerradas en el CM (no reservables) y desde cuándo.
- **FR-017**: El aviso de horizonte MUST incluir las noches con precio pero cerradas (próximos 365 días, sin reservas ni bloqueos del host) con la primera fecha.
- **FR-018**: "Abrir/Bloquear" del calendario MUST avisar cuando el CM no confirma el cambio de disponibilidad.
