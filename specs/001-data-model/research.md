# Research — Modelo de datos del dominio

Decisiones técnicas que resuelven los puntos abiertos del Technical Context. Formato: Decisión / Justificación / Alternativas.

## 1. Representación de dinero (COP)

- **Decisión**: `Numeric(12, 2)` mapeado a `decimal.Decimal` en Python. Una sola moneda por propiedad (campo `currency`, default `COP`).
- **Justificación**: Evita errores de punto flotante en cálculos de precios/descuentos. `Numeric` preserva exactitud. Aunque el COP suele usarse sin decimales, 2 decimales no estorban y dejan margen.
- **Alternativas**: `float` (descartado: imprecisión); enteros en unidades menores (innecesario para una sola moneda y añade fricción de lectura).

## 2. ORM y estilo de modelos

- **Decisión**: SQLAlchemy 2.0 con clases tipadas (`Mapped[...]`, `mapped_column(...)`) sobre el `DeclarativeBase` existente. Acceso async (`AsyncSession`, asyncpg).
- **Justificación**: Tipado estático (principio IV), API moderna 2.0, ya está en el scaffold. Async encaja con FastAPI.
- **Alternativas**: SQLModel (capa extra sobre SQLAlchemy+Pydantic, menos control de migraciones); ORM síncrono (no aprovecha async de FastAPI).

## 3. Precio efectivo: derivado vs. persistido

- **Decisión**: Persistir solo el **precio base** por (unidad, día). El **precio efectivo** se calcula en una función pura del dominio (`app/domain/pricing.py`) a partir de base + promociones vigentes + reglas (clamp a min/max). No se almacena.
- **Justificación**: Evita estado duplicado que se desincroniza. La derivación es barata y testeable. La trazabilidad (SC-004) se logra explicando el cálculo, no guardándolo.
- **Alternativas**: Persistir efectivo (cache) — se aplaza hasta que el rendimiento lo exija; introduce invalidación.

## 4. Promociones solapadas

- **Decisión**: Función pura que, dado un día, toma las promociones vigentes y aplica **solo la de mayor descuento efectivo**; no se acumulan (clarificación Q1).
- **Justificación**: Determinista, simple, coincide con la decisión del host.
- **Alternativas**: Acumular descuentos (rechazado por el host); prioridad manual (más complejo, innecesario ahora).

## 5. Auditoría y rollback

- **Decisión**: Tabla `PriceChangeLog` **append-only**: cada cambio de precio base guarda (propiedad, unidad, día, valor anterior, valor nuevo, timestamp, origen[chat|manual|suggestion|rollback], referencia opcional a sugerencia y a mensaje de chat). El **rollback** crea un nuevo registro con `origin=rollback` que fija el valor anterior. Si existen registros posteriores para la misma (unidad, día) que el cambio objetivo, se marca **conflicto** y la operación exige confirmación explícita (clarificación Q2).
- **Justificación**: Historial inmutable (no se reescribe), reversible y trazable (principio III). La detección de conflicto evita sobrescrituras silenciosas.
- **Alternativas**: Mutar el precio y guardar solo "última versión" (pierde historial); versionado tipo event-sourcing completo (sobre-ingeniería para el alcance).

## 6. Disponibilidad compartida entre canales

- **Decisión**: La disponibilidad vive a nivel de **(UnitType, fecha)** en `CalendarDay` (unidades disponibles / reservadas), NO por canal. Los `Channel` son atributos de la propiedad y referencian un id externo opaco. Las `Booking` reducen disponibilidad sin importar el canal de origen.
- **Justificación**: Refleja la realidad del channel manager (Beds24): una sola bolsa de inventario por unidad; vender en un canal bloquea los demás (SC-003). Evita modelar disponibilidad N veces.
- **Alternativas**: Disponibilidad por (canal, unidad, fecha) — produciría inconsistencias y overbooking; descartado.

## 7. Identificadores externos (channel manager / OTA)

- **Decisión**: Campos `external_ref` opacos (string) en `Property`, `UnitType`, `Channel`, `Booking` para mapear con Beds24/OTA, sin lógica de proveedor en el dominio.
- **Justificación**: Principio II (provider-agnostic). El adapter (feature #9) llena estos campos; el dominio no los interpreta.
- **Alternativas**: Tablas específicas por proveedor (acopla el dominio a Beds24).

## 8. Eventos y deduplicación

- **Decisión**: `Event` con `dedup_key` único = normalización de (nombre + fecha + lugar). Inserciones idempotentes (upsert por `dedup_key`).
- **Justificación**: Cumple FR-013/SC-006 sin duplicados aunque varias búsquedas devuelvan el mismo evento.
- **Alternativas**: Deduplicar por similitud difusa (complejo; se puede añadir luego).

## 9. Estados de sugerencia (máquina de estados)

- **Decisión**: `PriceSuggestion.status` ∈ {proposed, approved, rejected, applied}. Transiciones: proposed→approved→applied, proposed→rejected. `applied` enlaza al `PriceChangeLog` resultante.
- **Justificación**: Modela el flujo human-in-the-loop (proponer→aprobar→aplicar) con trazabilidad (FR-014/FR-015).
- **Alternativas**: Booleanos sueltos (menos claro, permite estados imposibles).

## 10. Config de LLM y parámetros flexibles

- **Decisión**: `LLMConfig` con campos fijos (provider, model_general, model_actions, budget) y un campo `params` JSONB para parámetros variables (temperatura, etc.). Single-tenant: una fila activa.
- **Justificación**: Estable para lo conocido, flexible para lo variable. JSONB evita migraciones por cada parámetro nuevo.
- **Alternativas**: Tabla clave-valor (más verboso); todo en columnas fijas (rígido).

## 11. Estrategia de pruebas con Postgres

- **Decisión**: Tests de dominio (`app/domain/pricing.py`) puros, sin DB. Tests de modelos/auditoría contra Postgres (docker compose) con rollback de transacción por test. La lógica de precio/promos/rollback se prueba sobre todo a nivel de dominio.
- **Justificación**: La mayor parte del valor (cálculo de precio, promos, rollback) es lógica pura → tests rápidos y deterministas. Postgres real para validar mapeos/constraints.
- **Alternativas**: SQLite en memoria (difiere de Postgres en tipos/JSONB/constraints; riesgo de falsos verdes).

## Puntos sin NEEDS CLARIFICATION pendientes

Ninguno. Las dos ambigüedades de negocio se resolvieron en `/speckit-clarify` (promos solapadas, semántica de rollback).
