# Feature Specification: Página pública e informe gratis

**Branch**: `030-public-report` · **Created**: 2026-10-14 · **Status**: Draft · **Input**: issue #147 (Feature 030, épica #156 Comercial Fase 0)

## Decisiones del host (2026-10-14)
1. **Registro abierto con cupo**: cualquiera se registra sin invitación (correo verificado o Google) hasta un cupo de beta que el administrador de plataforma ajusta en Administración (por defecto 50 cuentas). Lleno el cupo, el visitante deja su correo en lista de espera. Las invitaciones siguen funcionando y no cuentan contra el cupo.
2. **Municipios**: lista fija con **todos los municipios de Colombia** (también pueblos turísticos como Sabaneta, Guatapé o Villa de Leyva); se elige de la lista, sin texto libre.
3. **Precios**: el visitante escribe su precio normal por noche (y, si quiere, el de viernes/sábado); el informe muestra el precio sugerido en cada evento con el mismo cálculo de la app. No se inventan precios de mercado (eso es la #148).
4. **Muestra gratis y completo con cuenta**: gratis, los 3 eventos más importantes de los próximos 6 meses con su precio sugerido; con cuenta, los 6 meses completos en la app y por correo.

### Ajustes tras la prueba en staging (2026-10-14)
5. **Horizonte de 3 meses** (las agendas públicas rara vez publican más allá): el informe promete "próximos 3 meses" y, con cuenta, se actualiza cada semana.
6. **Correo con resumen** (5 eventos + enlace al informe en vivo), no la lista completa: el valor vive en la app.
7. **Resumen semanal por correo** cada lunes (noches de las próximas 2 semanas con sugerencia, enlaces para aplicarlo sin conexión y eventos nuevos de la zona); se apaga desde el correo (enlace firmado) o en Ajustes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Informe gratis en un minuto (Priority: P1)
Un anfitrión llega a staylever.com sin cuenta, elige su municipio, escribe su precio normal por noche y ve los 3 eventos más importantes de los próximos 6 meses con el precio que debería cobrar esas noches.

**Why this priority**: es el gancho comercial: muestra el valor sin pedir nada.

**Independent Test**: en una ventana privada, pedir el informe de "Sabaneta, Antioquia" con 250.000 COP y ver hasta 3 eventos con fechas, importancia y precio sugerido.

**Acceptance Scenarios**:
1. **Given** un municipio con eventos guardados de hace menos de 7 días, **When** el visitante pide el informe, **Then** lo ve en segundos y sin costo de búsqueda.
2. **Given** un municipio que nadie ha pedido, **When** lo pide y hay presupuesto del día, **Then** StayLever busca sus eventos, los guarda y muestra el informe.
3. **Given** el presupuesto diario de búsquedas agotado y un municipio sin eventos guardados, **When** lo pide, **Then** ve un mensaje honesto y puede dejar su correo para recibir el informe cuando esté listo.
4. **Given** un municipio sin eventos relevantes, **When** pide el informe, **Then** ve un mensaje claro (sin inventar eventos) y la invitación a crear la cuenta para recibir avisos cuando aparezcan.
5. **Given** un precio de fin de semana, **When** un evento cae en viernes o sábado, **Then** el precio sugerido parte del precio de fin de semana.

### User Story 2 — Informe completo al crear la cuenta (Priority: P1)
Desde el informe, el visitante pulsa "Ver los 6 meses completos", se registra sin invitación (si hay cupo), acepta términos y entra a la app con su apartamento sin conexión ya prellenado (municipio y precios). Ve el informe completo en la app y lo recibe por correo.

**Why this priority**: convierte el interés en una cuenta beta activa.

**Independent Test**: desde el informe de un municipio, registrarse con un correo nuevo, confirmar el correo y ver el formulario de apartamento prellenado y el informe completo; revisar el correo recibido.

**Acceptance Scenarios**:
1. **Given** cupo disponible, **When** el visitante se registra con correo o Google sin invitación, **Then** se crea su cuenta y cuenta contra el cupo.
2. **Given** el cupo lleno, **When** intenta registrarse sin invitación, **Then** ve que la beta está llena y puede dejar su correo en la lista de espera (con consentimiento).
3. **Given** una invitación válida, **When** se registra con ella, **Then** funciona aunque el cupo esté lleno y no consume cupo.
4. **Given** una cuenta recién creada desde el informe, **When** entra por primera vez, **Then** el formulario de "Usar sin conexión" trae el municipio y los precios del informe.

### User Story 3 — Página de inicio pública (Priority: P2)
Quien llega a staylever.com sin sesión ve una página que explica qué hace StayLever, para quién es (anfitriones con 1–5 apartamentos en Airbnb y Booking), cómo se ve la app, preguntas frecuentes, el informe gratis y "Únete a la beta", con enlaces a términos y privacidad, en español, inglés y portugués, claro/oscuro y en el celular.

**Independent Test**: abrir staylever.com en ventana privada (computador y celular), cambiar idioma y tema, y recorrer las secciones.

**Acceptance Scenarios**:
1. **Given** un visitante sin sesión, **When** abre staylever.com, **Then** ve la página pública (no la pantalla de entrar).
2. **Given** un usuario con sesión, **When** abre staylever.com, **Then** entra a la app como hoy.
3. **Given** la beta llena, **When** se ve la página, **Then** "Únete a la beta" lleva a la lista de espera.

### User Story 4 — Cupo, lista de espera y medición para el administrador (Priority: P2)
El administrador de plataforma ve en Administración el cupo (usado/total) y lo cambia, ve la lista de espera (correos y fecha, para invitar), y ve contadores diarios: visitas a la página, informes generados, municipios pedidos, búsquedas gastadas, registros y conversión informe → cuenta.

**Independent Test**: en Administración subir el cupo de 50 a 60, ver la lista de espera y los contadores del día después de pedir un informe y registrarse.

**Acceptance Scenarios**:
1. **Given** cupo 50 con 50 usadas, **When** el admin lo sube a 60, **Then** el registro abierto vuelve a funcionar.
2. **Given** correos en lista de espera, **When** el admin invita uno, **Then** recibe la invitación y sale de la lista.

### Edge Cases
- Abuso: un mismo visitante pide decenas de informes → límite diario por visitante y, para correos, por correo; mensaje amable al llegar al límite.
- Robots: si el abuso aparece pese a los límites, se puede activar un captcha del proveedor sin cambiar el flujo.
- Municipios con nombre repetido en distintos departamentos (p. ej. "La Unión") → la lista siempre muestra "Municipio, Departamento".
- Municipio dentro de un área metropolitana (Sabaneta → Medellín): el informe incluye también los eventos de la ciudad principal cercana.
- Precio vacío, cero o absurdo → validación con mensaje claro.
- Un correo que ya tiene cuenta intenta registrarse de nuevo → mensaje de "ya tienes cuenta, entra".
- La búsqueda de eventos falla → el visitante ve lo que haya guardado o el mensaje del escenario 1.3; no se gasta presupuesto doble.
- Cuentas borradas (028) liberan cupo.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001** staylever.com muestra la página pública a quien no tiene sesión; con sesión, la app como hoy. La actual /welcome lleva a la nueva página.
- **FR-002** La página pública está en es/en/pt, claro/oscuro, se ve bien en celular y enlaza términos y privacidad.
- **FR-003** El informe se pide con: municipio (de la lista oficial de municipios de Colombia, mostrado como "Municipio, Departamento"), precio normal por noche (obligatorio), precio de viernes/sábado (opcional), tipo de apartamento (opcional, informativo) y moneda COP por defecto.
- **FR-004** El informe cubre los próximos 6 meses y usa el mismo cálculo de sugerencia que la app (subida según importancia del evento: baja, media, alta). No muestra precios de mercado.
- **FR-005** Gratis se muestran los 3 eventos más importantes (por importancia y luego por fecha), con nombre, fechas, importancia y precio sugerido; el resto se indica como cantidad ("y 9 eventos más con cuenta").
- **FR-006** Los eventos de un municipio se reutilizan si se buscaron hace menos de 7 días (por el escaneo diario de las cuentas o por otro informe); si no, se buscan una vez y se guardan para todos.
- **FR-007** Un presupuesto diario global (configurable, por defecto 20 municipios nuevos al día) limita las búsquedas públicas; agotado, solo se sirve lo guardado.
- **FR-008** Límite de informes por visitante (por defecto 10 al día) y de envíos por correo (3 al día por correo). El visitante se identifica de forma no reversible (sin guardar su IP en claro).
- **FR-009** Registro abierto sin invitación (correo verificado o Google) mientras haya cupo; el cupo (por defecto 50) lo cambia el administrador de plataforma; las cuentas por invitación y la del administrador no cuentan; las borradas liberan cupo.
- **FR-010** Con el cupo lleno, el registro abierto ofrece la lista de espera: correo + consentimiento explícito para avisarle de la beta; el correo se usa solo para eso, se puede borrar a pedido y se borra al invitarlo o a los 12 meses.
- **FR-011** Al registrarse desde un informe, la cuenta nueva ve el informe completo (6 meses) en la app y lo recibe por correo una vez, y el formulario "Usar sin conexión" llega prellenado con municipio y precios.
- **FR-012** Medición sin cookies de terceros ni rastreo individual: contadores diarios agregados (visitas a la página pública, informes, municipios pedidos, búsquedas gastadas, registros abiertos, registros desde informe, entradas a lista de espera), visibles solo para el administrador de plataforma.
- **FR-013** El administrador ve y cambia el cupo y el presupuesto diario, ve la lista de espera e invita desde ella.
- **FR-014** Aislamiento: el informe público solo usa datos públicos (eventos por municipio); nunca muestra datos de ninguna cuenta (precios, reservas, nombres).
- **FR-015** Ley 1581: la política de privacidad se actualiza con el informe público, la lista de espera y la medición agregada.

### Key Entities
- **Municipio**: municipio oficial de Colombia (nombre, departamento, código oficial, ciudad principal del área metropolitana si aplica).
- **Búsqueda de municipio (caché)**: cuándo se buscaron por última vez los eventos de un municipio y con qué resultado.
- **Informe público**: municipio, precios dados, fecha; sin datos personales (solo un identificador no reversible del visitante para el límite).
- **Lista de espera**: correo, idioma, fecha, consentimiento, municipio de interés (opcional), estado (esperando / invitado).
- **Configuración de la beta**: cupo, presupuesto diario de búsquedas públicas.
- **Métrica diaria**: fecha, tipo de contador, valor.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001** Un visitante obtiene su informe gratis en menos de 1 minuto desde que llega a la página (en menos de 5 s si el municipio ya está guardado).
- **SC-002** Un visitante pasa del informe a la cuenta con el apartamento prellenado en menos de 3 minutos.
- **SC-003** El gasto de búsquedas públicas nunca supera el presupuesto diario configurado.
- **SC-004** Ningún informe muestra datos de una cuenta; ninguna IP queda guardada en claro.
- **SC-005** El administrador ve cada día cuántas visitas, informes, registros y entradas a la lista de espera hubo.
- **SC-006** Los ~449 tests existentes siguen pasando; producción no cambia para la cuenta del host.

## Assumptions
- La lista oficial de municipios (DANE/DIVIPOLA, ~1.100) se incluye en la app y no cambia a menudo.
- Para municipios de un área metropolitana se toma la ciudad principal (Medellín, Bogotá, Cali, Barranquilla, Bucaramanga, Cúcuta, Pereira) como fuente adicional de eventos.
- Los eventos encontrados para el informe se guardan como los del escaneo diario (datos públicos por municipio) y luego sirven a cuentas de ese municipio.
- Los festivos nacionales no se agregan de forma fija en esta feature (solo aparecen si la búsqueda los encuentra); puede ser una mejora posterior.
- El correo del informe completo usa el servicio de correo actual y la dirección hello@staylever.com.
- El captcha no se activa en la primera versión; se deja la opción documentada.
- Fuera de alcance: precios de mercado/competencia (#148), cobro, campañas, reclutamiento (#149), SEO avanzado.
