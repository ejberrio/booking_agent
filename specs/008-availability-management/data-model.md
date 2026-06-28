# Data Model — Gestión de disponibilidad

## Entidades existentes (reutilizadas, sin cambios de columnas)

### CalendarDay (ya existe)
Disponibilidad por unidad y noche. Campos relevantes:
- `unit_type_id`, `date`
- `units_available: int` — unidades disponibles esa noche (0 = sin disponibilidad).
- `is_blocked: bool` — **True = cerrada manualmente por el host** (distinto de reservada).

**Estados derivados de una noche** (para UI y agente):
| Estado | Condición |
|--------|-----------|
| disponible | `units_available > 0` |
| reservada | `units_available == 0` y cubierta por una `Booking` confirmada |
| bloqueada | `is_blocked == True` |
| sin datos | no hay `CalendarDay` (available = null) |

### Booking (ya existe)
Reserva confirmada (`status`, `check_in`, `check_out`). **Intocable** por esta feature: define qué noches no se pueden bloquear ni abrir.

## Entidad nueva

### AvailabilityChangeLog (NUEVO — migración)
Auditoría de cada cambio de disponibilidad (FR-007).

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `unit_type_id` | FK unit_type | |
| `date` | date | noche afectada |
| `old_units_available` | int \| null | antes |
| `new_units_available` | int | después |
| `was_blocked` | bool | is_blocked antes |
| `is_blocked` | bool | is_blocked después |
| `origin` | enum `ChangeOrigin` | manual / chat |
| `created_at` | timestamp | (TimestampMixin) |

- Un registro por noche afectada (no por las omitidas).
- Reutiliza el enum `ChangeOrigin` existente.
- La reversión es la operación inversa (no se usa este log para rollback automático; es trazabilidad).

## Transiciones de estado (noche)

```
disponible  --bloquear-->  bloqueada      (units_available=0, is_blocked=true)
bloqueada   --abrir----->  disponible     (units_available=units_count, is_blocked=false)
reservada   --(cualquiera)-> reservada    (OMITIDA: nunca se altera)
sin datos   --bloquear-->  bloqueada      (se crea CalendarDay)
```

## Invariantes

- Cero overbooking: una noche con reserva confirmada nunca pasa a `units_available>0` por esta feature, ni se cierra (ya está ocupada).
- Idempotencia: bloquear lo bloqueado / abrir lo disponible no cambia nada (0 noches afectadas).
- Toda noche afectada genera exactamente un `AvailabilityChangeLog`.
