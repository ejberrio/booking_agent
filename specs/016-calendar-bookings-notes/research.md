# Research: Feature 016 — Detalle de reservas y notas del host

**Date**: 2026-07-03 · Método: OpenAPI oficial de Beds24 V2 + lectura del código.

## R1. ¿El Channel Manager reporta el nombre del huésped?

- **Hallazgo (verificado en `apiV2.yaml` descargado del sitio oficial)**: el schema `booking` de V2 incluye `firstName` y `lastName` en `GET /bookings` (los mismos que ya usamos para channel/referer). No requiere scopes adicionales.
- **Decision**: `RemoteBooking.guest_name: str | None` — campo ÚNICO neutro; el adaptador V2 compone `"{firstName} {lastName}".strip()` (parciales permitidos; vacío → None). El V1 legacy devuelve None (honesto, no se investiga: V1 está deprecada).
- **Alternatives considered**: dos campos first/last en el puerto (propietario de Beds24, innecesario para mostrar); pedir el email/teléfono (fuera de alcance, más dato personal sin caso de uso).

## R2. Import: cuándo se corrige el nombre en re-imports

- **Decision**: al crear → set siempre. En reserva existente → actualizar solo si el remoto trae un nombre no vacío distinto del local (nunca borrar un nombre local porque el remoto venga vacío en una corrida). Cuenta en `updated_count` (patrón del fix de channel_kind, feature 012).
- **Rationale**: el remoto es la fuente de verdad cuando HABLA; su silencio no es información.

## R3. Endpoint de reservas para la web

- **Decision**: `GET /bookings?unit_type_id&date_from&date_to` (router nuevo) — reservas CONFIRMADAS cuya estancia solapa el rango (`check_in <= date_to AND check_out > date_from`, noches [in, out)); orden por check_in. Respuesta con `nights` calculado y `channel` token.
- **Rationale**: mismo criterio de solape que los KPIs (#97); el cruce por día lo hace el cliente (patrón 014/015: `/pricing/calendar` intacto, FR-009/FR-010 por construcción). "El día de salida no ocupa": un booking cubre días `d` con `check_in <= d < check_out` — el cliente usa esa regla.
- **Alternatives considered**: enriquecer CalendarDayView (acoplamiento + regresión, rechazado de nuevo); reutilizar el tool del agente (no es HTTP y su salida está pensada para el LLM).

## R4. Modelo CalendarNote y validación

- **Decision**: tabla plana `calendar_note`: `unit_type_id` FK, `date_from`, `date_to` (NOT NULL ambos; día único = from==to), `text` String(500) no vacío, timestamps. Validación: texto 1–500 tras strip; `date_from <= date_to`. Solapes permitidos sin límite. CRUD `/calendar-notes` (GET por unidad, POST, PATCH parcial, DELETE real) sin fingerprint.
- **Rationale**: las notas son memoria del host, no auditoría ni escritura al canal → mismo criterio que NativeDeal (015). Rango cerrado (a diferencia de los deals) porque una nota "para siempre" no tiene caso de uso y complica el marcado.
- **Alternatives considered**: nota anclada al bloqueo (`AvailabilityChangeLog`) — acoplaría la nota a UNA operación; el host quiere anotar rangos aunque no estén bloqueados; JSON en CalendarDay (una nota por día, rompe rangos/solapes).

## R5. UI: panel único y marcador

- **Decision**: componente nuevo `DayInfoPanel` en la columna lateral, visible cuando hay selección: (a) sección **Reservas** solo si la selección es UN día con reservas de esa noche — huésped (o "sin nombre"), canal display, `llegada → salida`, noches, estado, ref; (b) sección **Notas** — lista de notas que cubren la selección con editar/borrar inline + textarea para crear una nota sobre TODO el rango seleccionado (integra con la selección por arrastre existente: seleccionar 19-21 oct y anotar "reserva personal de Fulano" en un gesto). Marcador de nota: punto **lima** (`bg-lime-500`; ocupados: rojo/gris/ámbar/violeta/cian) + leyenda condicional.
- **Rationale**: un solo panel evita apilar 4 tarjetas (sugerencias/ofertas/día ya conviven); la creación sobre el rango seleccionado es el flujo natural del caso típico (bloqueo de varios días).

## R6. Privacidad del nombre (FR-003)

- **Decision**: el nombre viaja solo API→web (proxy autenticado). El middleware de logging existente registra `method path status ms` (sin query ni body) → nunca loguea nombres. El tool `get_bookings` del agente NO gana el campo en esta feature.
- **Rationale**: minimizar superficie de un dato personal; el chat no lo necesita hoy (si el host lo pide, será decisión explícita futura).
