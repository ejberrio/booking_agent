# Feature Specification: Consultar y reportar eventos ("¿Falta un evento?")

**Branch**: `035-report-events` · **Created**: 2026-10-16 · **Input**: conversación con el anfitrión tras la feature 034.

## Contexto y decisión
El descubrimiento de eventos ya corre solo:
- boleteras y agendas: semanal y gratis;
- festivos: semanal y gratis;
- búsquedas dirigidas: semanales, ≈ USD 0,25 al mes por ciudad;
- búsquedas generales: diarias, ≈ USD 0,50 al mes por ciudad.

Todo se comparte entre las cuentas de la misma área.

Un botón de "buscar eventos ahora" **no** se implementa:
- casi no aporta, porque las agendas cambian pocas veces por semana;
- cuesta en cada clic (USD 0,02–0,05);
- carga más a las boleteras, contra lo que pide el memorando legal.

En su lugar:
1. **Consultar eventos** desde el asistente. Lee lo ya guardado: $0 en búsquedas.
2. **Reportar un evento que falta.** El anfitrión aporta lo que sabe de su zona y StayLever lo **verifica** con una sola búsqueda (≈ USD 0,02) antes de compartirlo.

## User Stories
1. **(P1)** El anfitrión pregunta en el chat "¿qué eventos hay en diciembre cerca de mi apartamento?" y ve los eventos de su municipio, su área metropolitana y los festivos, con fechas, recinto, importancia y origen (boletera, búsqueda, festivo o reportado).
2. **(P1)** El anfitrión reporta "Hebert Vargas, 4 de diciembre, DAVIarena", desde el chat o desde **Sugerencias → ¿Falta un evento?**:
   - si ya existe, se le dice que ya está y no se gasta nada;
   - si no, StayLever lo verifica con una búsqueda. Si se confirma, lo agrega para todas las cuentas de esa área y recalcula las sugerencias de esas fechas para su cuenta;
   - si no se confirma, lo guarda como **nota privada** en su calendario y no afecta a nadie más.
3. **(P2)** Tope de **3 reportes al día por cuenta**. El costo queda registrado en el uso de IA de la cuenta (027), aparte del tope de 5 búsquedas diarias que gasta el escaneo.

## Requirements
- **FR-001** Herramienta de lectura del asistente `get_events(date_from, date_to)`: área de la propiedad (`municipalities.area_keys`) + festivos, máximo 60 eventos, sin costo de búsqueda.
- **FR-002** `POST /events/report` y herramienta `report_event(name, start_date, end_date?, venue?)`. Validaciones:
  - nombre de 3 a 200 caracteres;
  - fecha entre hoy y +400 días;
  - fin ≥ inicio y máximo 31 días.
- **FR-003** Antes de buscar se revisan los duplicados (nombre parecido el mismo día en el área): resultado `exists`, sin costo.
- **FR-004** Verificación con 1 búsqueda dirigida y 1 extracción con IA, ambas medidas en `ai_usage`. Se confirma si algún resultado trae un evento de nombre parecido en la misma fecha.
  - **Confirmado:** el recinto conocido fija el municipio y la importancia; si no, el municipio es el de la propiedad. Luego se recalculan las sugerencias de esas fechas.
  - **No confirmado:** nota en el calendario de la cuenta ("Evento reportado sin confirmar: …").
- **FR-005** `event_report` (por cuenta): nombre, fechas, recinto, estado (`exists` | `verified` | `unverified`), evento vinculado y fecha. Sirve para el tope diario y para auditar.
- **FR-006** El reporte no publica precios ni crea sugerencias aplicadas. Las sugerencias se siguen aprobando (principio III).
- **FR-007** Aislamiento (principio VI):
  - el reporte y la nota son de la cuenta;
  - solo el evento **verificado** pasa a la tabla pública de eventos de la ciudad;
  - nunca se guardan datos de huéspedes.

## Success Criteria
- Reportar un evento que ya existe cuesta $0 y responde en menos de 1 s.
- Un evento real reportado aparece en las sugerencias de la cuenta en menos de 30 s.
- Nadie puede gastar más de 3 verificaciones al día por cuenta.

## Tasks
- [x] T001 Modelo `EventReport` (por cuenta) + migración `b8c9d0e1f2a4`
- [x] T002 `app/services/event_report_service.py`: `list_events`, `report` (duplicados → verificación → evento compartido o nota privada), `report_metered` (uso medido), tope de 3 al día
- [x] T003 Rutas `GET /events`, `POST /events/report`; herramientas del asistente `get_events` y `report_event`
- [x] T004 Web: botón "¿Falta un evento?" en Sugerencias (es/en/pt)
- [x] T005 Tests `tests/test_event_report.py` (área + festivos, existe sin costo, confirmado con recálculo, nota privada, tope, aislamiento)
