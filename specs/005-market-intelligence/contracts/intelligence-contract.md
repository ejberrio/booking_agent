# Contrato — Inteligencia de mercado

## Interfaces provider-agnostic

```python
# app/search/base.py
class SearchProvider(Protocol):
    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]: ...

# app/market/reference.py
class MarketReference(Protocol):
    async def get(self, zone: str, day: date) -> Decimal | None: ...
```
`TavilyProvider` implementa `SearchProvider`; `BaselineMarket` implementa `MarketReference` (lee `market_reference`). Ambos inyectables (dobles en tests).

## Extracción (LLM inyectable)

```python
# app/market/extractor.py
async def extract_events(llm, results: list[SearchResult]) -> list[EventCandidate]: ...
# Usa el LLM para parsear; descarta candidatos sin fecha utilizable.
```

## Heurística pura

```python
# app/domain/suggestion.py
def suggest_price(base, *, event_relevance, occupancy_high, market_ref, min_price, max_price) -> SuggestionOutput: ...
# evento: alta+30/media+15/baja+5 %, ocupación alta +10 %, acercar a market_ref si existe,
# acotar a [min,max]; devuelve (precio, justificación, confianza).
```

## Servicios

```python
# suggestion_engine.py
async def generate_suggestions(session, *, unit_type_id, date_from, date_to, market) -> list[PriceSuggestion]: ...
#   por día: relevancia del evento (Event), ocupación (CalendarDay), market.get(zone,day) -> suggest_price
#   crea PriceSuggestion(proposed) si no hay equivalente vigente.

# intelligence_service.py
async def scan(session, search, llm, market, *, queries, unit_type_id, date_from, date_to) -> IntelligenceRun: ...
#   buscar -> extraer (LLM) -> upsert eventos (event_service) -> generate_suggestions -> registra IntelligenceRun.
async def apply_suggestion(session, channel, suggestion_id) -> PriceSuggestion: ...
#   aprueba+aplica vía pricing_app_service (origen=sugerencia: audita+publica); status=applied; enlaza el cambio.
```

## Endpoints (`/suggestions`)

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/suggestions` | lista sugerencias (filtro por estado/fechas) |
| POST | `/suggestions/{id}/approve` | marca aprobada |
| POST | `/suggestions/{id}/reject` | marca rechazada |
| POST | `/suggestions/{id}/apply` | aplica vía 003 (audita origen=sugerencia + publica) |

## Garantías de comportamiento

- **G1**: cada `PriceSuggestion` tiene día/rango, precio, justificación y confianza.
- **G2**: el precio sugerido está dentro de [min,max] (acotado por la heurística).
- **G3**: una sugerencia equivalente no se re-propone si ya hay una vigente/aplicada/rechazada.
- **G4**: aplicar audita con origen=sugerencia y publica el efectivo; sin aprobación no se aplica.
- **G5**: sin `MarketReference`, las sugerencias se generan igual.
- **G6**: eventos deduplicados; candidatos sin fecha se descartan.
- **G7**: el agente puede listar sugerencias (lectura) sin inventar.

## Contrato de pruebas (dobles: search/LLM/market/channel falsos)

| Test | Verifica |
|------|----------|
| `test_suggestion_engine::test_high_event_high_occupancy_raises` | evento alto + ocupación alta → sube; justificación menciona el evento (G1) |
| `test_suggestion_engine::test_clamped_to_limits` | el sugerido nunca excede min/max (G2) |
| `test_suggestion_engine::test_no_signal_no_change` | sin evento/ocupación/mercado → no propone cambio (FR-006) |
| `test_suggestion_engine::test_works_without_market` | market None → genera igual (G5) |
| `test_intelligence_service::test_scan_dedup_and_no_reproposal` | eventos dedup; no re-propone equivalente (G3, G6) |
| `test_intelligence_service::test_apply_origin_suggestion_publishes` | aplicar audita origen=sugerencia + publica (G4) |
| `test_intelligence_service::test_apply_requires_no_auto` | nada se aplica sin la acción de aplicar/aprobar (G4) |
