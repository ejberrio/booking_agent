# Contrato: Escritura de disponibilidad en el puerto ChannelManager

## Puerto (app/channels/base.py)

Se añade al `Protocol`:
```python
async def set_availability_range(
    self, room_external_id: str, date_from: date, date_to: date, num_avail: int
) -> WriteResult: ...
```
- `num_avail=0` cierra; `num_avail>=1` abre.
- Devuelve `WriteResult(ok, verified, detail)` (verificación por relectura), igual que `set_rate_range`.

## Beds24 V2 (beds24_v2.py)

`POST /inventory/rooms/calendar`:
```json
[{ "roomId": 697411, "calendar": [{ "from": "2026-07-01", "to": "2026-07-03", "numAvail": 0 }] }]
```
- Verificación: releer con get_rates y comparar `available == num_avail`.
- Errores: `ChannelError` → lo gestiona `sync_service.publish_availability` (incidencia).

## Beds24 V1 (beds24.py)

Implementa el método para cumplir el puerto pero lanza `ChannelError("V1 no soporta escritura")` (sus escrituras están muertas; producción usa V2).

## Reglas
- Provider-agnostic: el dominio llama al puerto, no a Beds24.
- Sin secretos en logs/errores (redacción ya existente en el adapter).
