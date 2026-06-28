# Quickstart — Gestión de disponibilidad

Cómo validar la feature (local y en prod, vía el proxy con cookie `session=ok`).

## Por chat

1. **Bloquear**: "cierra del 1 al 3 de julio" → el agente propone *"Propongo bloquear N noche(s)…"* (omitiendo reservas) → confirmar → noches cerradas y publicadas.
2. **Bloquear con filtro**: "bloquea los fines de semana de agosto" → solo sáb/dom del rango.
3. **Reabrir**: "vuelve a abrir el 2 de julio" → propone abrir → confirmar → disponible de nuevo.
4. **Solicitud de disponibilidad NO propone precio**: "quita la disponibilidad de X" → propuesta de **bloqueo** (no de precio).
5. **Respeta reservas**: pedir bloquear un rango que incluye una noche reservada → esa noche se omite y se informa.

## Por calendario (web)

1. Seleccionar un día/rango → botón **Bloquear** o **Abrir** → preview (noches afectadas/omitidas) → **Confirmar**.
2. El calendario distingue visualmente: disponible, **reservada**, **bloqueada**, sin datos.

## Verificación

- **App**: `GET /pricing/calendar` muestra `is_blocked=true` y `available=0` en las noches cerradas; al abrir, `available>0` y `is_blocked=false`.
- **Beds24**: relectura confirma `numAvail=0` (cerrado) / `numAvail>=1` (abierto).
- **Reservas intactas**: una noche con reserva sigue `available=0` y nunca se reabre por error.
- **Publicación resiliente**: si Beds24 falla, el cambio local persiste y aparece una incidencia en `/sync/issues`.
- **Auditoría**: cada noche afectada deja un `AvailabilityChangeLog` (origen chat/manual).

## Comandos (prod, vía proxy)

```bash
WEB=https://web-production-dfcaf.up.railway.app
# preview de bloqueo
curl -s -X POST -H "Cookie: session=ok" -H "Content-Type: application/json" \
  -d '{"unit_type_id":1,"action":"block","selection":{"date_from":"2026-07-01","date_to":"2026-07-03"}}' \
  "$WEB/api/proxy/pricing/availability/preview"
```
