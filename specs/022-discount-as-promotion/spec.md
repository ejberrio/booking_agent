# Feature Specification: Bajar precios con promoción (sin tocar el precio base)

**Feature Branch**: `022-discount-as-promotion`
**Created**: 2026-10-09
**Status**: Draft
**Input**: User description: "Bajar precios con promoción en vez de tocar el precio base (Feature 022, issue #128)."

## Contexto

Hoy, aplicar una sugerencia —incluidas las que **bajan** el precio— cambia el **precio base** de la noche. El host prefiere que las bajadas se hagan como **promoción temporal**: el precio base queda como referencia de valor, el huésped ve una oferta y la promoción termina sola al pasar sus fechas. Las **subidas** siguen cambiando el precio base (eventos y mercado lo justifican).

Además, hoy hay descuentos de las plataformas que se **acumulan** sobre cualquier precio: 10 % por reservar desde el celular en Booking.com y en Airbnb, 5 % semanal y 25 % mensual en Airbnb. Una promoción del 11 % más el 10 % móvil deja la noche casi un 20 % más barata para quien reserve desde el celular.

Decisiones del host (2026-10-09):
1. **Toda** bajada sugerida se aplica **siempre como promoción**; el precio base nunca baja por una sugerencia.
2. **Piso** = un **precio mínimo por noche en COP** que define el host: la promoción se recorta para que el precio final, contando los descuentos que siempre se acumulan, no baje de ese mínimo.
3. La promoción se publica en **Booking.com y Airbnb**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Las bajadas se aplican como promoción (Priority: P1)

Como host, cuando aplico sugerencias a la baja desde la pestaña Sugerencias, quiero que se creen **promociones temporales** en Booking.com y Airbnb para esas noches, en vez de bajar el precio base; y que las subidas del mismo lote sigan cambiando el precio base.

**Why this priority**: es el pedido central; sin esto el resto no aporta.

**Independent Test**: seleccionar un bloque "Libre próximo" (−11 %) y uno de evento (+30 %), confirmar el lote: la noche del evento cambia su precio base; las noches libres conservan su precio base y aparece una promoción "StayLever · Libre próximo 20–22 oct" del 11 % publicada en ambos canales, visible en Ofertas y en el calendario.

**Acceptance Scenarios**:

1. **Given** un bloque a la baja seleccionado, **When** el host confirma, **Then** se crea una promoción por cada tramo de noches seguidas con el mismo descuento, publicada en Booking.com y Airbnb, y el precio base de esas noches **no cambia**.
2. **Given** un lote con subidas y bajadas, **When** el host confirma, **Then** las subidas cambian el precio base y las bajadas crean promociones, todo con una sola confirmación.
3. **Given** promociones creadas desde sugerencias, **When** el host mira Ofertas o el calendario, **Then** se distinguen de las creadas a mano (marca "desde sugerencias") y muestran su nombre, fechas y descuento.
4. **Given** la publicación de una promoción falla en el canal, **When** termina el lote, **Then** el resultado lo dice por noche, la promoción no queda como activa y la sugerencia sigue pendiente.
5. **Given** "Aplicar solo esta" sobre una sugerencia a la baja, **When** se confirma, **Then** también se aplica como promoción.

---

### User Story 2 - Precio mínimo que nunca se cruza (Priority: P1)

Como host quiero definir un **precio mínimo por noche** y que ninguna promoción creada por sugerencias deje el precio final por debajo, incluso contando el descuento del celular.

**Why this priority**: sin piso, las bajadas y los descuentos de las plataformas se acumulan sin control y se pierde dinero.

**Independent Test**: con mínimo $230.000, base $270.000 y descuento móvil 10 %, una sugerencia del −15 % (que daría $229.500 −10 % = $206.550 desde el celular) se recorta al descuento máximo que respeta el mínimo, y la vista previa lo explica.

**Acceptance Scenarios**:

1. **Given** un precio mínimo configurado, **When** la promoción de una noche llevaría el precio final con descuentos acumulables por debajo del mínimo, **Then** el descuento se recorta lo justo para respetarlo y la vista previa muestra "recortado por el precio mínimo".
2. **Given** que ni siquiera un descuento del 1 % respeta el mínimo, **When** se previsualiza, **Then** esa noche se omite con motivo "por debajo del precio mínimo".
3. **Given** que no hay precio mínimo configurado, **When** el host previsualiza bajadas, **Then** la vista previa advierte "Sin precio mínimo configurado" con acceso directo a Ajustes; aplicar sigue siendo posible (con el tope actual del motor, −15 % por sugerencia).
4. **Given** Ajustes, **When** el host define o cambia el precio mínimo, **Then** se guarda y aplica a las vistas previas siguientes.

---

### User Story 3 - Ver el precio real que pagará el huésped (Priority: P2)

Como host quiero ver en la vista previa, por noche y por canal: precio base, % de la promoción, precio con promoción y precio desde el celular (con los descuentos que se acumulan), más advertencias de acumulación y de solapes con otras promociones.

**Why this priority**: es la información para decidir con seguridad; el lote funciona sin ella, pero a ciegas.

**Independent Test**: la vista previa de una bajada en Airbnb muestra $270.000 → −11 % → $240.300 → desde el celular $216.270; y avisa que existen descuentos semanal (5 %) y mensual (25 %) que pueden sumarse en estadías largas.

**Acceptance Scenarios**:

1. **Given** una bajada, **When** se previsualiza, **Then** cada noche muestra base, % promoción, precio con promoción y precio desde el celular por canal.
2. **Given** descuentos condicionales (por estadía larga, anticipación) registrados, **When** se previsualiza, **Then** aparecen como advertencia informativa (no cuentan para el piso).
3. **Given** otra promoción activa que se solapa en fechas, **When** se previsualiza, **Then** se advierte el solape con su nombre y se requiere confirmarlo explícitamente.

---

### User Story 4 - Ninguna promoción olvidada (Priority: P3)

Como host quiero que las promociones creadas por sugerencias terminen solas al acabar sus fechas y poder retirarlas antes si la situación cambia (por ejemplo, la noche se reservó o el mercado subió).

**Why this priority**: higiene y control; las fechas ya limitan el riesgo.

**Independent Test**: una promoción de sugerencias cuyas noches pasaron aparece como "finalizada"; una vigente se puede retirar desde Ofertas con confirmación y deja de aplicar en ambos canales.

**Acceptance Scenarios**:

1. **Given** una promoción cuyas fechas ya pasaron, **When** el host mira Ofertas, **Then** aparece como finalizada (no como activa).
2. **Given** una promoción de sugerencias vigente cuyas noches quedaron todas reservadas, **When** el host mira Ofertas, **Then** se indica "sin noches libres" y se ofrece retirarla.
3. **Given** el host retira una promoción, **When** confirma, **Then** deja de aplicar en ambos canales y la sugerencia de origen queda registrada como aplicada y luego retirada.

---

### Edge Cases

- Noches seguidas con distinto % → una promoción por tramo de igual %.
- Bloque a la baja con noches ya reservadas → esas noches se omiten (como hoy en el lote).
- Sugerencia cuya bajada es menor al 1 % tras recortar → se omite (no vale la pena una promoción).
- Promoción de sugerencias que se solapa con otra promoción creada a mano → advertencia y confirmación explícita; nunca se modifica la del host.
- Precio mínimo mayor que el precio base de alguna noche → esa noche no admite promoción (omitida con motivo).
- Descuento móvil registrado solo para un canal → el piso se calcula por canal; la promoción usa el % que respeta el piso en **ambos** canales.
- Cambio de idioma: nombres y motivos visibles en es/en/pt; el nombre que ven los huéspedes en las plataformas va en español (como las promociones actuales).

## Requirements *(mandatory)*

### Functional Requirements

**Aplicar bajadas como promoción (US1)**

- **FR-001**: Al aplicar sugerencias (en lote o "solo esta"), las noches cuyo precio sugerido es **menor** que el precio base vigente MUST aplicarse como promoción temporal; el precio base de esas noches MUST NOT cambiar.
- **FR-002**: Las noches cuyo precio sugerido es **mayor o igual** que el base MUST seguir aplicándose como cambio de precio base (comportamiento actual).
- **FR-003**: Las bajadas MUST agruparse en una promoción por tramo de noches seguidas con el mismo % de descuento, con nombre "StayLever · {bloque} {fechas}" y publicada en Booking.com y Airbnb.
- **FR-004**: Subidas y bajadas del mismo lote MUST previsualizarse juntas y confirmarse **una sola vez** (preview → huella → confirmar).
- **FR-005**: Si la publicación de una promoción falla, MUST NOT quedar activa ni marcar como aplicadas sus sugerencias; el resultado MUST informarlo por noche.
- **FR-006**: Las promociones creadas desde sugerencias MUST distinguirse de las creadas a mano y enlazarse a sus sugerencias de origen.

**Precio mínimo (US2)**

- **FR-007**: El host MUST poder definir, cambiar y quitar un **precio mínimo por noche (COP)** en Ajustes.
- **FR-008**: El descuento de cada promoción MUST recortarse para que, en cada canal, el precio con promoción menos los descuentos **siempre acumulables** de ese canal no quede por debajo del mínimo; si ningún descuento ≥ 1 % lo respeta, la noche MUST omitirse con motivo.
- **FR-009**: Sin precio mínimo configurado, la vista previa MUST advertirlo y permitir continuar con el tope actual del motor.

**Transparencia (US3)**

- **FR-010**: La vista previa MUST mostrar por noche y canal: precio base, % promoción, precio con promoción y precio con descuentos siempre acumulables.
- **FR-011**: Los descuentos registrados MUST clasificarse como **siempre acumulables** (p. ej. móvil) o **condicionales** (p. ej. semanal, mensual, anticipación); los condicionales MUST mostrarse como advertencia informativa.
- **FR-012**: Los solapes con otras promociones activas MUST advertirse por nombre y requerir confirmación explícita.

**Ciclo de vida (US4)**

- **FR-013**: Las promociones cuyas fechas terminaron MUST mostrarse como finalizadas.
- **FR-014**: El host MUST poder retirar una promoción de sugerencias vigente con confirmación; deja de aplicar en ambos canales.
- **FR-015**: Una promoción de sugerencias sin noches libres restantes MUST señalarse en Ofertas.

**Transversal**

- **FR-016**: Todo texto nuevo visible MUST estar en español, inglés y portugués.
- **FR-017**: Nada se publica sin la confirmación explícita del host (Principio III).

### Key Entities

- **Promoción** (existente): nombre, fechas, % de descuento, canales, estado; gana **origen** (manual / sugerencia) y el enlace a sus sugerencias.
- **Precio mínimo** (nuevo ajuste): valor en COP por noche, opcional.
- **Descuento registrado / deal nativo** (existente): gana la clasificación **siempre acumulable** o **condicional**.
- **Sugerencia** (existente): una bajada aplicada queda enlazada a su promoción.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 bajadas aplicadas desde sugerencias que cambien el precio base.
- **SC-002**: Con precio mínimo configurado, 0 noches cuyo precio con promoción y descuentos siempre acumulables quede por debajo del mínimo.
- **SC-003**: Aplicar un lote mixto (subidas + bajadas) sigue requiriendo **una** vista previa y **una** confirmación.
- **SC-004**: El host identifica en ≤ 10 s, desde Ofertas, qué promociones vienen de sugerencias y cuáles terminaron.
- **SC-005**: 0 promociones de sugerencias mostradas como activas después de su última noche.

## Assumptions

- Los descuentos de las plataformas se tratan como acumulables en el peor caso (piso conservador), aunque Booking.com/Airbnb a veces no los combinen.
- Clasificación inicial de los deals registrados: "Mobile" → siempre acumulable; "semanal", "mensual", "early bird", "last minute" → condicional; el host puede cambiarla.
- La promoción usa el mismo mecanismo de promociones por rango que ya publica la app (feature 011) y el mismo nombre en ambos canales.
- El tope del motor (−15 % por sugerencia) se mantiene; el precio mínimo es un control adicional.
- Las promociones de sugerencias no se retiran automáticamente cuando una noche se reserva (la promoción solo afecta reservas nuevas); se señalan para que el host decida.
