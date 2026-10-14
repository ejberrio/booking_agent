# Feature Specification: Asistente con cambios en bloque y una sola confirmación

**Feature Branch**: `032-assistant-bulk` · **Created**: 2026-10-14 · **Input**: issue #172 (revisión del asistente)

## Problema
El asistente solo propone un precio absoluto por rango, procesa una herramienta por respuesta, permite una sola propuesta pendiente y no sabe aplicar ni rechazar sugerencias ni crear descuentos por días de semana. Confirmar gasta un mensaje de la cuota (#144) y la propuesta no se ve en detalle.

## User Stories
1. **(P1) Cambio de precio en bloque.** "Sube 10 % del 10 al 20 de diciembre", "pon 350.000 los viernes y sábados de enero", "baja 20.000 estas fechas": UNA propuesta, precio calculado por noche en el servidor, omite pasadas, reservadas/bloqueadas, sin precio y fuera de límites; una confirmación.
2. **(P1) Sugerencias desde el chat.** "Aplica las sugerencias de noviembre" / "rechaza las de bajada": usa las mismas reglas que el botón Aplicar (subidas al base, bajadas como promoción con piso del precio mínimo); quedan aplicadas/rechazadas y no reaparecen.
3. **(P1) Descuentos por noche y días de semana.** "15 % de descuento los martes de enero": % sobre el precio de CADA noche, respetando el precio mínimo y los descuentos que se acumulan; tramos contiguos como promociones; avisos de solapes, reservas y doble descuento en la vista previa.
4. **(P1) Una confirmación clara.** La propuesta trae una tabla (tramos, noches, antes → después, omitidas por motivo, avisos) en el chat; botones Confirmar/Cancelar que no pasan por la IA ni gastan cuota; un "sí" escrito sigue funcionando.
5. **(P1) Instrucciones actualizadas.** Multicanal genérico (Channel Manager), regla de lote, fin de semana = noches de viernes y sábado, moneda de la propiedad, sin herramientas viejas.

## Requirements
- FR-001 `propose_price_change`: modos set / percent / amount, rango con días de semana o fechas sueltas, redondeo; ≤ 366 noches; precio > 0; variación > ±50 % rechazada.
- FR-002 `get_suggestions` con id, unidad, rango, precio actual vs sugerido, dirección y noches vendibles; `propose_apply_suggestions` y `propose_reject_suggestions` por ids o filtros (≤ 100).
- FR-003 `propose_discount`: % o precio, días de semana o fechas, estancia mínima, canales; ≤ 31 tramos.
- FR-004 Una `AgentAction` por propuesta con vista previa estructurada; el orquestador ejecuta todas las lecturas de una respuesta y exige una sola propuesta.
- FR-005 `POST /chat/actions/{id}/confirm|cancel` deterministas, aislados por cuenta, sin cuota.
- FR-006 Herramientas legacy (`propose_create_promotion`, `propose_delete_promotion`) fuera del catálogo del modelo; `propose_set_day`/`propose_set_range` siguen funcionando como alias.
- FR-007 Todo id que mande el modelo se valida contra la cuenta (principio VI); escrituras solo tras confirmación (principio III).

## Success Criteria
- SC-001 "sube 10 % del 10 al 20" con precios distintos → 1 propuesta y 1 confirmación, cada noche con su +10 %.
- SC-002 "aplica las sugerencias de noviembre" → mismas noches y mismos resultados que el lote de la pantalla Sugerencias.
- SC-003 "15 % los martes de enero" → 1 confirmación y una promoción por tramo.
- SC-004 Confirmar con los botones no consume cuota ni llama a la IA.
