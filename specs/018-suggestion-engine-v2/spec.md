# Feature Specification: Motor de sugerencias v2 — explicable, con contexto de la propiedad y precio de mercado

**Feature Branch**: `018-suggestion-engine-v2`
**Created**: 2026-07-04
**Status**: Draft (clarify COMPLETADO 2026-07-04: agrupación por evento/rango; tope bajista −15%; POIs semilla Daviarena + CC Mayorca; ventana de hueco 14 días)
**Input**: Issue #98 — Sugerencias menos genéricas: que digan QUÉ evento, DÓNDE y POR QUÉ; que conozcan la ubicación y los sitios cercanos relevantes (Daviarena, inauguración sep-nov 2026 muy cerca del apto); que el precio se base también en el MERCADO de la zona. Feedback del host (2026-07-03): el motor solo sugiere SUBIDAS (faltan señales bajistas) y acumula duplicados por fecha (~130 pendientes). Decisión tomada: estrategia "Ambos" — puerto de datos de mercado con implementación gratis (Tavily) ahora y proveedor pago (AirDNA/PriceLabs) enchufable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sugerencias explicables (Priority: P1)

Como host, quiero que cada sugerencia diga exactamente por qué: qué evento es (nombre, lugar, fechas, fuente), qué dice el mercado y cómo se llegó al precio sugerido, para decidir en segundos con la información delante en la lista, el calendario y el chat.

**Acceptance Scenarios** (resumen):
1. Una sugerencia por evento muestra: nombre del evento, lugar, fechas, enlace/fuente, y el desglose del % ("evento high +30% · ocupación alta +10% · mercado de la zona ~X").
2. Una sugerencia sin evento (solo mercado u ocupación) explica esas señales igual de claro.
3. El racional estructurado se ve en la lista, el panel del calendario (feature 014) y las respuestas del chat sin cambios de formato entre superficies.

---

### User Story 2 - Señales bajistas: también sugerir bajar (Priority: P1)

Como host, quiero que el motor sugiera BAJAR el precio cuando hay señales de baja demanda (huecos próximos sin reservar, temporada valle sin eventos, mercado por debajo del mío), para llenar noches que se van a quedar vacías — nunca por debajo del mínimo de mi regla de precios.

**Acceptance Scenarios** (resumen):
1. Noches libres dentro de los próximos 14 días (ventana decidida por el host) sin reserva ni evento → sugerencia de descuento con su porqué ("quedan N días y la fecha sigue libre; el mercado está en X").
2. El descuento respeta el piso (min_price de la regla) y el tope de −15% por sugerencia (decisión del host).
3. Con demanda alta la lógica alcista actual se conserva (y gana el desglose explicable).

---

### User Story 3 - Contexto de la propiedad: ubicación y POIs (Priority: P1)

Como host, quiero que el motor sepa dónde está el apartamento (ubicación desde el Channel Manager) y qué sitios relevantes tiene cerca — registro manual de POIs con nombre, distancia y fechas clave (p. ej. "Daviarena, inauguración sep-nov 2026") — para que las búsquedas de eventos sean dirigidas ("eventos en Daviarena", "conciertos cerca de CC Mayorca Sabaneta") y no genéricas de Medellín.

**Acceptance Scenarios** (resumen):
1. CRUD de POIs (nombre, nota de distancia, fechas relevantes opcionales, activo) en Configuración; semilla decidida por el host: Daviarena (inauguración sep-nov 2026, muy cerca) y CC Mayorca (al frente).
2. El scan usa la ubicación + POIs activos para armar sus consultas; los eventos encontrados guardan a qué POI/zona responden.
3. Un evento en un POI cercano pesa más que uno genérico de la ciudad (relevancia por cercanía).

---

### User Story 4 - Precio de mercado (estrategia "Ambos") (Priority: P2)

Como host, quiero que el precio sugerido se compare con el mercado de la zona en esas fechas — hoy con el proveedor gratuito (búsquedas dirigidas de tarifas publicadas), mañana con uno pago (AirDNA/PriceLabs) sin reescribir el motor — para vender al mejor precio, no solo relativo a mi precio propio.

**Acceptance Scenarios** (resumen):
1. Con referencia de mercado disponible, la sugerencia la usa y la cita en el racional ("mercado de la zona ~$X según N tarifas encontradas, fuente y fecha").
2. Sin datos de mercado (búsqueda sin resultados), el motor lo dice honesto y sugiere solo con las señales propias (nunca inventa números).
3. Cambiar de proveedor (gratis ↔ pago) es configuración, no código del motor; el plan investiga APIs/planes de AirDNA/PriceLabs y deja el puerto listo.
4. Ocupación esperada de la zona (Airbnb): best-effort del proveedor; límites documentados honestamente.

---

### User Story 5 - Sin duplicados: superseder por fecha (Priority: P1)

Como host, quiero que un nuevo scan REEMPLACE la sugerencia pendiente de la misma fecha (si la señal cambió) en lugar de acumular otra, para no volver a tener 130 sugerencias con dos versiones por noche.

**Acceptance Scenarios** (resumen):
1. Scan nuevo con señal distinta para una fecha con sugerencia pendiente → la anterior queda reemplazada (estado terminal "superseded", auditable) y solo la nueva aparece como pendiente.
2. Señal equivalente → no se crea nada (dedup actual se conserva).
3. Las resueltas (aplicadas/rechazadas) nunca se tocan.
4. Migración de lo acumulado: el primer scan v2 supersede las pendientes v1 (por-día) cuyas fechas queden cubiertas por las nuevas sugerencias de rango, y las totalmente vencidas; las resueltas no se tocan.

---

### Edge Cases (selección)

- Fechas con reserva confirmada: no se sugiere nada (no tiene efecto).
- Evento de POI con rango de fechas incierto ("sep-nov"): sugerencias por sub-rango confirmable o señal de relevancia amplia con confianza menor.
- Presupuesto del proveedor gratis (créditos Tavily/mes): las búsquedas dirigidas se acotan (config de nº de consultas por scan) y el scan reporta si se quedó corto.
- Mercado con pocas muestras (1-2 tarifas): confianza baja y racional que lo dice.
- POI inactivo o vencido (inauguración pasada): deja de dirigir búsquedas.

## Requirements (resumen — se completará tras clarify)

- **FR-001** Racional estructurado por sugerencia (evento con nombre/lugar/fechas/fuente; señales; desglose del %) visible en lista/calendario/chat.
- **FR-002** Señales bajistas (huecos libres a ≤14 días, valle sin eventos, mercado por debajo) con piso en min_price y tope de −15% por sugerencia.
- **FR-003** Ubicación de la propiedad desde el CM + registro manual de POIs (CRUD local, semilla del host) que dirigen las búsquedas.
- **FR-004** Puerto de datos de mercado con implementación gratuita (búsquedas dirigidas) y proveedor pago enchufable por configuración; honestidad total cuando no hay datos.
- **FR-005** Supersede por fecha: pendiente anterior reemplazada (estado auditable), nunca duplicados; resueltas intactas.
- **FR-006** Agrupación por evento/rango: una sugerencia cubre el rango del evento; las señales de ocupación/mercado agrupan días contiguos con la misma señal en un solo rango.
- **FR-007** Configuración de búsqueda editable (zona, nº de consultas por scan, tipos de evento, POIs).
- **FR-008** Sin romper los 221 tests; el flujo aprobar-y-aplicar (014) y el marcado del calendario funcionan sin cambios para las sugerencias v2.

## Assumptions (previas al clarify)

- El scan sigue siendo diario (cron existente); los créditos gratis de Tavily (~1000/mes) alcanzan con ~10-20 consultas dirigidas por corrida.
- AirDNA/PriceLabs: investigación de APIs/planes en el plan (research); esta feature entrega el puerto + proveedor gratis; contratar el pago es decisión futura del host.
- La ocupación "esperada" de Airbnb sin API pública es best-effort del proveedor de mercado; los límites se documentan.
