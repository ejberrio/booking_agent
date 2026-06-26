# Implementation Plan: Inteligencia de mercado y sugerencias de precio

**Branch**: `005-market-intelligence` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/005-market-intelligence/spec.md`

## Summary

Backend de inteligencia: una **búsqueda web** provider-agnostic (Tavily) descubre eventos de Medellín; el **LLM** configurado los parsea a datos estructurados que se deduplican en `Event` (001). Una **referencia de mercado** simple (baseline configurable por zona) vive detrás de una interfaz. Un **motor de sugerencias heurístico y explicable** combina relevancia de evento (+30/+15/+5%), ocupación alta (+10%) y la referencia de mercado, acotando a los límites, y produce `PriceSuggestion` (001) con justificación y confianza. El host **revisa, aprueba/rechaza y aplica**; aplicar reutiliza el motor de precios (003) → audita (origen=sugerencia) y publica el efectivo a Beds24 (002). Un **escaneo diario** (cron) lo automatiza, idempotente. El agente (004) puede consultar sugerencias. Pruebas con búsqueda/LLM/mercado **simulados**.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: httpx (Tavily), el cliente LLM de la feature 004 (parsing, inyectable), SQLAlchemy async, Pydantic; reutiliza `Event`/`PriceSuggestion` + `event_service`/`suggestion_service` (001), `pricing_app_service` (003), conector (002), tools del agente (004)  
**Storage**: PostgreSQL 16 (reutiliza tablas; añade `intelligence_run` y `market_reference`)  
**Testing**: pytest + pytest-asyncio; SQLite async; **SearchProvider falso**, **LLM falso** (extracción guionizada), **MarketReference falsa**, **ChannelManager falso**  
**Target Platform**: Servidor Linux (API en `apps/api`)  
**Project Type**: Web (backend de esta feature)  
**Integration**: búsqueda web (Tavily) y mercado tras interfaces; parsing de eventos con el LLM (gpt-4o-mini); aplicación de sugerencias vía el motor de precios (003)  
**Constraints**: sugerencias explicables y propuestas (host aprueba); aplicaciones auditadas (origen=sugerencia) y reversibles; heurística acotada a límites; bajo volumen y caché para acotar costo de búsqueda; escaneo idempotente  
**Scale/Scope**: 1 host, Medellín, horizonte ~3-6 meses de eventos; volumen pequeño

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| I. Spec-Driven | Procede de spec.md (005) con clarificaciones. ✅ |
| II. Provider-agnostic | Búsqueda y mercado detrás de interfaces; LLM inyectable; nada propietario en el dominio. ✅ |
| III. Human-in-the-loop | Sugerencias propuestas; el host aprueba; aplicar audita (origen=sugerencia) y es reversible. ✅ |
| IV. Tipado y pruebas | Motor de sugerencias **puro** y testeable; escaneo con dobles (search/LLM/market/channel falsos). ✅ |
| V. Simplicidad | Heurística transparente; mercado simple en v1; solo 2 tablas nuevas. ✅ |

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/005-market-intelligence/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── intelligence-contract.md   # interfaces (search/market/extractor) + engine + endpoints + tests
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/api/app/
├── search/                       # NUEVO
│   ├── base.py                   # SearchProvider (Protocol) + SearchResult (DTO)
│   └── tavily.py                 # TavilyProvider (httpx) con caché simple
├── market/                       # NUEVO
│   ├── extractor.py              # parseo de resultados → EventCandidate vía LLM (inyectable)
│   └── reference.py              # MarketReference (Protocol) + BaselineMarket (zona→precio)
├── domain/
│   └── suggestion.py             # NUEVO: heurística PURA (suggest_price: evento+ocupación+mercado→precio/justif/conf)
├── services/
│   ├── suggestion_engine.py      # NUEVO: genera PriceSuggestion por día/rango (usa domain + datos locales)
│   └── intelligence_service.py   # NUEVO: scan(eventos+mercado→sugerencias), apply_suggestion (vía 003), IntelligenceRun
├── models/
│   └── intelligence.py           # NUEVO: IntelligenceRun, MarketReference
├── api/routes/
│   └── suggestions.py            # NUEVO: GET /suggestions; POST /suggestions/{id}/approve|reject|apply
└── agent/
    └── tools.py                  # + herramienta de lectura get_suggestions (004)

apps/api/scripts/scan_daily.py    # NUEVO: cron de escaneo + generación de sugerencias
apps/api/migrations/versions/     # NUEVA migración: intelligence_run, market_reference
apps/api/tests/
├── test_suggestion_engine.py     # heurística pura (evento/ocupación/mercado; acotar a límites)
└── test_intelligence_service.py  # scan con dobles (dedup, no re-proponer aplicadas); apply audita origen=sugerencia + publica
```

**Structure Decision**: Interfaces nuevas (`search`, `market`) e inyectables; heurística PURA en `app/domain/suggestion.py`; orquestación en `suggestion_engine`/`intelligence_service`. Aplicar una sugerencia reutiliza `pricing_app_service` (003) → audita (origen=sugerencia) y publica. 2 tablas nuevas (`IntelligenceRun`, `MarketReference`); `Event`/`PriceSuggestion` ya existen (001). El agente (004) gana una herramienta de lectura `get_suggestions`.

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
