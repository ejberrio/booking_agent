# Feature Specification: Eventos del área metropolitana en las sugerencias

**Branch**: `033-metro-events` · **Created**: 2026-10-16 · **Input**: hallazgo del anfitrión al probar la feature 030

## Problema
El informe gratis (030) une los eventos del municipio con los de la ciudad principal del área
metropolitana (Sabaneta → Medellín), pero las sugerencias diarias, la extensión de precios y el
resumen semanal solo usaban los del municipio de la propiedad.

## Requirements
- FR-001 `municipalities.area_keys(city)`: municipio + ciudad principal (Valle de Aburrá, Bogotá-Sabana, Cali, Barranquilla, Bucaramanga, Cúcuta, Pereira); texto libre de la propiedad ("Medellín, Antioquia").
- FR-002 Sugerencias (`suggestion_engine`), extensión de precios (eventos de relevancia alta) y resumen semanal usan esas claves; el mismo evento visto en dos ciudades cuenta una vez (`event_service.unique_events`, nombre normalizado + fecha).
- FR-003 Escaneo diario: la ciudad principal se reutiliza si alguien la buscó en los últimos 7 días (`city_scan`); si no, se busca una vez con la búsqueda medida de la cuenta.
- FR-004 Sin cambios para propiedades en la ciudad principal (la cuenta del anfitrión está en Medellín).

## Tasks
- [x] T001 `area_keys`, `by_city_key` en `app/domain/municipalities.py`; `name_key`/`unique_events` en `event_service`
- [x] T002 `suggestion_engine`, `price_extension_service`, `digest_service` con las claves del área
- [x] T003 `scan_daily._refresh_area` (caché 7 días + búsqueda medida)
- [x] T004 Tests `tests/test_metro_events.py` (Sabaneta sí, Guatapé no, sin duplicados, caché del escaneo)
