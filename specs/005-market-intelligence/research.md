# Research — Inteligencia de mercado y sugerencias

Formato: Decisión / Justificación / Alternativas.

## 1. Búsqueda web tras interfaz (Tavily), inyectable

- **Decisión**: `SearchProvider` (Protocol) con `TavilyProvider` (httpx) y una caché simple en memoria/DB por consulta+período. Inyectable → en tests un `FakeSearch` devuelve resultados guionizados.
- **Justificación**: Provider-agnostic (II), testeable sin red ni créditos (IV), costo acotado (FR-013).
- **Alternativas**: Brave/Serper (mismo contrato, futuro); llamar la API directo sin interfaz (acopla).

## 2. Extracción de eventos con LLM

- **Decisión**: `event_extractor` usa el cliente LLM (feature 004, inyectable) para convertir el texto de los resultados en `EventCandidate` estructurado (nombre, fecha(s), tipo, relevancia, ubicación). Salida validada (descarta sin fecha utilizable). En tests, un LLM falso devuelve candidatos guionizados.
- **Justificación**: Robusto con texto libre (clarificación); reutiliza el LLM ya configurado; bajo volumen + caché acotan costo.
- **Alternativas**: reglas/keywords (frágil con texto libre); descartado por más falsos negativos.

## 3. Referencia de mercado: baseline simple tras interfaz

- **Decisión**: `MarketReference` (Protocol) con `BaselineMarket` que lee una tabla `market_reference` (zona → precio de referencia, con `source`). En v1 es un baseline configurable; si no hay dato para la zona/fecha, devuelve `None` y las sugerencias se generan igual.
- **Justificación**: Clarificación (referencia simple en v1, sugerencias funcionan sin mercado); evita scraping frágil y costos.
- **Alternativas**: derivar de búsqueda web (ruidoso/costoso); aplazar mercado del todo (menos informado).

## 4. Heurística de sugerencia (pura, explicable, configurable)

- **Decisión**: Función pura `suggest_price(base, event_relevance, occupancy_high, market_ref, min, max)`:
  - Factor por evento: alta +30%, media +15%, baja +5%, sin evento 0%.
  - Ocupación alta: +10% adicional.
  - Precio objetivo = base × (1 + factores). Si hay `market_ref`, se acerca al promedio entre objetivo y referencia.
  - **Se acota a [min, max]**. Confianza = combinación de señales presentes (evento/ocupación/mercado).
  - Devuelve (precio sugerido, justificación legible, confianza). Parámetros en constantes/settings.
- **Justificación**: Transparente y testeable (clarificación); cumple FR-004/FR-005.
- **Alternativas**: solo eventos (menos preciso); LLM como motor de pricing (caja negra, no explicable) — descartado.

## 5. Aplicación de sugerencias vía el motor de precios (003)

- **Decisión**: Aprobar+aplicar usa `pricing_app_service` (003) para fijar el precio del día/rango de la sugerencia con **origen=sugerencia**, validando límites, auditando y **publicando** el efectivo. La sugerencia pasa a `applied` y enlaza el cambio. `approve`/`reject` usan `suggestion_service` (001).
- **Justificación**: Reutiliza el flujo auditado/publicado (DRY, III); no duplica lógica de pricing.
- **Alternativas**: aplicar con `set_base_price` sin publicar (001) — no llegaría a Booking.

## 6. Idempotencia y no re-proponer

- **Decisión**: Eventos deduplicados (`event_service`, por `dedup_key`). El motor NO crea una sugerencia equivalente (misma unidad/día/precio) si ya existe una `applied`/`rejected`/`proposed` vigente para ese día. El escaneo registra `IntelligenceRun`.
- **Justificación**: FR-012/SC-006 (idempotencia; no re-proponer aplicadas/rechazadas).
- **Alternativas**: regenerar todo cada corrida (ruido y duplicados).

## 7. Ocupación

- **Decisión**: `occupancy_high` se deriva del calendario (`CalendarDay.units_available` vs `units_count`): alta si la disponibilidad restante es 0 o ≤ un umbral configurable.
- **Justificación**: Usa datos locales ya sincronizados (002); simple y testeable.
- **Alternativas**: modelos de demanda (sobre-ingeniería para v1).

## 8. Escaneo programado y agente

- **Decisión**: `scripts/scan_daily.py` (cron) ejecuta buscar→extraer→upsert eventos, refrescar mercado y generar sugerencias, registrando `IntelligenceRun`. El agente (004) gana una herramienta de **lectura** `get_suggestions`.
- **Justificación**: Frescura automática (FR-011) e integración conversacional (FR-014), sin scheduler embebido.
- **Alternativas**: orquestador de tareas (innecesario a esta escala).

## Sin NEEDS CLARIFICATION pendientes

Fuente de mercado (baseline simple), heurística (porcentajes) y extracción (LLM) se resolvieron en `/speckit-clarify`.
