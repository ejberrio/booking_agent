# Feature Specification: Limpieza de eventos repetidos y con fecha equivocada

**Branch**: `036-event-dedupe` · **Created**: 2026-10-19 · **Input**: revisión de producción tras la 035. Del 1 al 10 de diciembre había "Martin Garrix" 4 veces (una con una fecha falsa, el 1-dic) y dos copias de "Hebert Vargas" (Sabaneta y Medellín).

## Causa
- Las búsquedas con IA de días anteriores guardaron el mismo evento con varios nombres ("Concierto de Juanes", "JUANES", "Juanes · World Tour 2026"…).
- La limpieza de la 034 solo comparaba dentro del mismo municipio, no en toda el área metropolitana.

## Requirements
- **FR-001 Al guardar un evento de búsqueda:** si ya existe uno de nombre parecido el mismo día en **cualquier municipio del área**, se reutiliza (`event_service.upsert_event` con `municipalities.area_keys`).
- **FR-002 Agrupación:** mismo día y nombre parecido a **cualquiera** del grupo (`event_groups`). Gana la mejor versión: fuente oficial (boletera o agenda), luego la más importante, luego la más antigua (`_rank`).
- **FR-003 Limpieza diaria** por área en el escaneo (`event_service.dedupe_area`):
  - fusiona los repetidos, completando recinto, fecha de fin e importancia;
  - borra los **conciertos encontrados por búsqueda** cuyo nombre se parece a un **concierto grande de una boletera** en otra fecha a ±10 días (fecha equivocada).
  - No toca ballet, teatro ni congresos, que pueden tener varias funciones, ni festivos ni otras áreas.
- **FR-004** `list_events`, el informe y las sugerencias muestran una sola versión por evento (la oficial).

## Resultado esperado en producción (simulación sin guardar, 19-oct-2026)
Área de Medellín: 252 eventos futuros → **156 repetidos fusionados** y **2 fechas equivocadas** borradas (Juanes 16-nov; Martin Garrix 1-dic).

## Tasks
- [x] T001 `event_groups`, `_rank`, `unique_events` (mejor versión); `upsert_event` dedupe en el área
- [x] T002 `dedupe_area` + llamada diaria en `scan_daily.refresh_event_sources`
- [x] T003 Tests `tests/test_event_dedupe.py` (fusión, fecha equivocada, grupos transitivos, ballet con varias funciones, otra área y festivos intactos)
