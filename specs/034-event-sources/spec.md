# Feature Specification: Fuentes de eventos (boleteras, agendas, festivos) y área en ambos sentidos

**Branch**: `034-event-sources` · **Created**: 2026-10-16 · **Input**: el anfitrión notó que Hebert Vargas (4-dic-2026, DAVIarena) nunca apareció. Investigación en `docs/research/eventos-fuentes-2026-10.md` y memorando legal en `docs/research/legal-datos-mercado-2026-10.md`.

## Causa
- Las búsquedas genéricas traen artículos de "agenda" sin conciertos privados.
- Solo 5 resultados por búsqueda y la dirección de la propiedad incluida en la consulta.
- Medellín no veía los eventos de Sabaneta (la DAVIarena), porque el área solo funcionaba en un sentido.
- El extractor no sabía la fecha de hoy.

## Requirements
- **FR-001 Área en ambos sentidos:** `area_keys` = municipio + ciudad principal + todos los municipios del área + `colombia` (festivos).
- **FR-002 Fuentes estructuradas, sin IA, una vez por semana por ciudad principal:**
  - TuBoleta: resultados por ciudad + cartelera de la DAVIarena + JSON-LD de cada ficha;
  - Ticketmaster Colombia: página por ciudad + JSON-LD;
  - Plaza Mayor: API The Events Calendar.
  
  El recinto conocido define el municipio y la importancia (≥10.000 personas = alta). Las cancelaciones borran el evento.
- **FR-003 Reglas (memorando legal):**
  - solo fuentes cuyos términos no prohíben el acceso automatizado;
  - robots.txt respetado;
  - sin evadir bloqueos (403/429/captcha → se registra y no se insiste);
  - User-Agent identificable `StayLeverBot/1.0`, ~1,5 s entre peticiones;
  - solo hechos públicos del evento;
  - interruptor `EVENT_SOURCES_DISABLED`.
- **FR-004 Festivos y puentes de Colombia** (Ley Emiliani + Ley 2578 de 2026, verificados contra nager.at): fines de semana largos (importancia media) y Semana Santa, Navidad y Año Nuevo (alta), con clave nacional.
- **FR-005 Búsquedas dirigidas semanales por ciudad principal:** 3 meses dentro de las boleteras (`include_domains`, 20 resultados, advanced) + noticias de la semana. Las consultas de ciudad ya no llevan la dirección; el extractor recibe la fecha de hoy.
- **FR-006 Sin duplicados:** el mismo día con un nombre parecido es un solo evento; la boletera manda (nombre, recinto, municipio, enlace).
- **FR-007** El resumen semanal no lista festivos como "eventos nuevos".

## Resultado verificado (lectura real, 16-oct-2026)
- Medellín: 63 eventos en ~2 min (TuBoleta 42, Ticketmaster 12, Plaza Mayor 9).
- **Hebert Vargas** aparece el 4-dic en la DAVIarena (Sabaneta), con importancia alta.
- 12 de las 14 fechas de la DAVIarena. Las otras 2: la ficha de Rubén Blades está rota en TuBoleta y la del 29-oct es un foro.

## Tasks
- [x] T001 `app/domain/holidays_co.py` (festivos y puentes)
- [x] T002 `municipalities.area_keys`/`keys_for`/`area_core_key` en ambos sentidos + `colombia`
- [x] T003 `app/data/venues_co.json` + `app/services/event_sources_service.py` (TuBoleta, Ticketmaster CO, Plaza Mayor, Fetcher respetuoso)
- [x] T004 `event_service.upsert_structured`, `similar_names`, `delete_by_source`, `seen_recently`
- [x] T005 Búsquedas dirigidas (Tavily con opciones), extractor con fecha, zona sin dirección
- [x] T006 `scan_daily.refresh_event_sources` (festivos + fuentes + dirigidas por ciudad principal)
- [x] T007 Tests `tests/test_event_sources.py`; conftest apaga las fuentes reales en las pruebas
