# Research: Sugerencias accionables (019)

## R1. ¿Cómo saber si una noche es vendible al momento de consultar?

- **Decision**: vendible = `d >= hoy` ∧ ninguna reserva `confirmed` con `check_in ≤ d < check_out` ∧ `calendar_day.is_blocked` falso ∧ no (`units_available == 0` sin bloqueo). Se calcula al listar/previsualizar con dos consultas por rango.
- **Rationale**: la reserva es la fuente de verdad que ya usa el calendario (PR #118) y cubre días pasados/inventario desactualizado; el inventario a 0 es el respaldo para reservas que no estén en la BD (p. ej. bloqueos del canal). El día de salida no ocupa (coherente con calendario y Beds24).
- **Alternatives**: marcar las sugerencias como `superseded` al entrar una reserva → no reaparecerían al cancelarse (viola FR-003); depender solo del scan → retraso de hasta 24 h.

## R2. ¿Dónde agrupar en bloques: API o web?

- **Decision**: API, en una función PURA (`app/domain/suggestion_blocks.py`), expuesta por `GET /suggestions/blocks`.
- **Rationale**: Principio IV (lógica que decide qué se aplica junto → tests en Python); la web solo pinta. Un único lugar para la regla evento/periodo.
- **Alternatives**: agrupar en el cliente → sin tests de dominio y duplicaría el cálculo de vendibles.

## R3. Clave de agrupación

- **Decision**: si la sugerencia tiene factor `event` → `event:<nombre normalizado>` (une días no contiguos del mismo evento); si no, `period:<kind dominante>` (`gap` u `occupancy`) uniendo solo días contiguos. Sugerencias v1 sin `factors` → `period:other` contiguo.
- **Rationale**: es lo que eligió el host ("por evento/periodo"); los eventos multi-fecha (p. ej. Martin Garrix 1 y 5 dic) quedan juntos; los huecos libres próximos se agrupan por tramos.
- **Alternatives**: por semana/mes (descartado por el host).

## R4. Huella anti-stale del lote

- **Decision**: sha256[:16] de `ids seleccionados ordenados` + por noche `fecha|sugerencia|precio_actual|precio_nuevo|válida|motivo`.
- **Rationale**: reutiliza el patrón de `fingerprint_for` (pricing) ampliado con la sugerencia y la validez, así que cubre cambios de precio, de ocupación (la noche pasa a omitida), de límites y de estado de la sugerencia.
- **Alternatives**: token con TTL → no detecta cambios de estado real.

## R5. Fallos de publicación parciales sin desalinear canal y app

- **Decision**: aplicar por tramos (días contiguos con igual precio) dentro de `session.begin_nested()`; si `publish_effective` reporta incidencias **o lanza una excepción**, rollback del savepoint (el precio local vuelve al anterior) y registrar `SyncIssue` fuera del savepoint. Las noches de ese tramo salen como `failed` y sus sugerencias siguen pendientes.
- **Rationale**: el apply individual (014) ya garantiza "nada queda aplicado si no se publicó" haciendo rollback total; en lote el equivalente granular es el savepoint por tramo. SQLAlchemy async soporta savepoints en PostgreSQL y SQLite (tests).
- **Alternatives**: publicar primero y persistir después → `publish_effective` calcula el precio efectivo desde la BD (promociones), habría que duplicar ese cálculo; rollback total del lote → un fallo en un tramo descartaría todo lo bueno.

## R6. Refresco del racional (US4)

- **Decision**: `_exists_equivalent` devuelve la fila; si está `proposed/approved` se sobrescriben `rationale` y `confidence` con los del cálculo actual.
- **Rationale**: mantiene identidad/estado (no hay churn de ids ni de selección en la UI) y elimina explicaciones obsoletas (caso real: Nov 28 seguía mostrando "mercado ~83000").
- **Alternatives**: superseder y recrear siempre → ids cambiantes cada día y la selección del host se perdería.
