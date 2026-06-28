# Contrato: Herramientas del agente (disponibilidad)

Dos herramientas de ESCRITURA nuevas (siguen el flujo propose→confirm como las de precio).

## propose_block_availability
- **Descripción**: "Propone CERRAR (bloquear) la disponibilidad de un rango (filtro opcional por días de semana). No aplica hasta confirmar; omite noches con reserva."
- **Parámetros**: `{ unit_type_id:int, date_from:str, date_to:str, weekdays?:int[] (0=lun..6=dom) }`

## propose_open_availability
- **Descripción**: "Propone REABRIR (abrir) la disponibilidad de un rango previamente bloqueado. No aplica hasta confirmar; no altera noches reservadas."
- **Parámetros**: `{ unit_type_id:int, date_from:str, date_to:str, weekdays?:int[] }`

## Comportamiento
- `build_proposal` genera un preview: nº de noches afectadas, nº omitidas (con motivo), aviso reforzado si es un cambio grande. Resumen tipo: *"Propongo bloquear 8 noche(s) (2 omitidas por reserva). ¿Confirmas?"*.
- Tras `confirm_pending`, `apply_proposal` aplica vía `availability_service` con `origin=chat` y publica a Beds24.
- El host confirma/cancela igual que con precios.

## Prompt del agente
- Se ELIMINA la regla "no puedes cambiar disponibilidad" y se AÑADE: "Para cerrar/abrir fechas usa `propose_block_availability` / `propose_open_availability`. Nunca uses herramientas de precio para solicitudes de disponibilidad."
- Mantiene la interpretación de estados (disponible / reservada / bloqueada / sin datos).

## Reglas
- Nunca propone bloquear/abrir noches con reserva confirmada (las omite e informa).
- Reversión = operación inversa (abrir deshace bloquear); no hay tool de rollback de disponibilidad.
