# Data Model — Modelo de datos del dominio

PostgreSQL 16 / SQLAlchemy 2.0 (async). Todas las tablas tienen `id` (PK, BigInteger o UUID), `created_at`, `updated_at` (timestamptz). Montos en `Numeric(12,2)`. Single-tenant (sin columna de tenant/usuario).

Convención: `external_ref` = identificador opaco del channel manager/OTA (lo llena el adapter; el dominio no lo interpreta).

## Diagrama de relaciones (resumen)

```text
Property 1───* Channel
Property 1───* UnitType
Property 1───* PricingRule (0..1 activa)
Property 1───* Promotion
UnitType 1───* CalendarDay        (por fecha)
UnitType 1───* Rate               (precio base por fecha)
UnitType 1───* Booking
Property 1───* PriceSuggestion ───0..1 PriceChangeLog (al aplicarse)
Rate/UnitType 1───* PriceChangeLog (historial por unidad/fecha)
Event            (independiente; referenciada por sugerencias vía justificación)
LLMConfig        (1 fila activa)
Conversation 1───* Message ───0..* PriceChangeLog (acción originada)
```

## Entidades

### Property
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| name | str | requerido |
| city | str | default "Medellín" |
| currency | str(3) | default "COP" |
| external_ref | str? | id en el channel manager |
| status | enum(active, inactive) | default active |

- Relaciones: `channels`, `unit_types`, `pricing_rules`, `promotions`, `suggestions`.

### Channel
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| property_id | FK→Property | |
| kind | enum(booking, airbnb, direct) | |
| is_active | bool | solo `booking` = true inicialmente |
| external_ref | str? | id del listado en la OTA |
| price_offset_pct | Numeric(5,2)? | **modelado, no aplicado** (channel-aware) |

- Constraint: único (property_id, kind).
- Nota: la disponibilidad NO cuelga de Channel (es compartida por UnitType).

### UnitType
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| property_id | FK→Property | |
| name | str | p. ej. "Apartaestudio" |
| units_count | int | nº de unidades físicas iguales |
| external_ref | str? | |

### CalendarDay
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| unit_type_id | FK→UnitType | |
| date | Date | |
| units_available | int | derivable de units_count − reservas/bloqueos |
| is_blocked | bool | bloqueo manual |

- Constraint: único (unit_type_id, date). Índice por (unit_type_id, date).
- Disponibilidad **compartida entre canales** (no hay dimensión de canal aquí).

### Rate (precio base por unidad y día)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| unit_type_id | FK→UnitType | |
| date | Date | |
| base_price | Numeric(12,2) | precio por noche (COP) |

- Constraint: único (unit_type_id, date). Índice por (unit_type_id, date).
- El **precio efectivo** NO se almacena: se calcula (ver contrato de dominio).

### PricingRule
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| property_id | FK→Property | |
| min_price | Numeric(12,2)? | límite inferior |
| max_price | Numeric(12,2)? | límite superior |
| parity_notes | str? | placeholder (paridad avanzada aplazada) |
| is_active | bool | |

### Promotion
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| property_id | FK→Property | |
| name | str | |
| discount_type | enum(percent, amount) | |
| discount_value | Numeric(12,2) | % o monto |
| start_date | Date | |
| end_date | Date | |
| conditions | JSONB? | condiciones opcionales |
| status | enum(active, inactive) | |

- Regla de negocio (dominio): si varias promociones cubren un día, se aplica **solo la de mayor descuento efectivo** (no se acumulan).

### Booking
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| unit_type_id | FK→UnitType | |
| channel_kind | enum(booking, airbnb, direct) | canal de origen |
| check_in | Date | |
| check_out | Date | |
| status | enum(confirmed, cancelled, pending) | |
| external_ref | str? | id de la reserva en la OTA |

- Las reservas confirmadas reducen `units_available` en el rango [check_in, check_out).

### Event
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| name | str | |
| start_date | Date | |
| end_date | Date? | |
| kind | enum(concert, fair, convention, holiday, festival, other) | |
| relevance | enum(low, medium, high) | impacto estimado |
| location | str? | recinto/zona |
| source_url | str? | |
| dedup_key | str | **único**: normaliza(name + start_date + location) |

### PriceSuggestion
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| property_id | FK→Property | |
| unit_type_id | FK→UnitType? | |
| date_from | Date | |
| date_to | Date | rango (un día → from==to) |
| suggested_price | Numeric(12,2) | |
| rationale | JSONB | refs a eventos/mercado/ocupación + texto |
| confidence | Numeric(4,3) | 0–1 |
| status | enum(proposed, approved, rejected, applied) | |
| applied_change_id | FK→PriceChangeLog? | enlace al aplicarse |

- Estados: proposed→approved→applied | proposed→rejected.

### PriceChangeLog (append-only)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| unit_type_id | FK→UnitType | |
| date | Date | día afectado |
| old_price | Numeric(12,2)? | null si no existía |
| new_price | Numeric(12,2) | |
| origin | enum(chat, manual, suggestion, rollback) | |
| suggestion_id | FK→PriceSuggestion? | |
| message_id | FK→Message? | mensaje de chat que lo originó |
| reverts_change_id | FK→PriceChangeLog? | si es un rollback |
| changed_at | timestamptz | |

- **Append-only**: nunca se actualiza/borra. Índice por (unit_type_id, date, changed_at).
- Rollback: nuevo registro con `origin=rollback` y `reverts_change_id`. Conflicto si existen registros con `changed_at` posterior al cambio objetivo para la misma (unit_type_id, date).

### LLMConfig
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| provider | str | p. ej. "openai" |
| model_general | str | "gpt-4o-mini" |
| model_actions | str | "gpt-4o" |
| budget_usd_per_day | Numeric(8,2)? | |
| params | JSONB | temperatura, etc. |
| is_active | bool | una fila activa |

### Conversation
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| title | str? | |
| started_at | timestamptz | |

### Message
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| conversation_id | FK→Conversation | |
| role | enum(user, assistant, system, tool) | |
| content | text | |
| created_at | timestamptz | |

- Una acción de cambio de precio se enlaza vía `PriceChangeLog.message_id`.

## Reglas de validación (resumen, verificadas en dominio/constraints)

1. `base_price` ≥ 0; respeta `PricingRule.min/max` (se señala si fuera de rango).
2. `discount_value` > 0; `start_date` ≤ `end_date`.
3. `Promotion` solapadas → aplica solo la de mayor descuento efectivo.
4. `Booking.check_in` < `check_out`.
5. `Event.dedup_key` único (upsert idempotente).
6. `PriceChangeLog` inmutable; rollback con detección de conflicto.
7. Disponibilidad nunca negativa; reserva no excede `units_count`.

## Fuera de alcance (espacio reservado, no implementado)

- `Channel.price_offset_pct` activo (precios por canal).
- Promociones específicas de Airbnb y paridad avanzada (`PricingRule.parity_notes` es solo nota).
- Multi-tenancy / múltiples usuarios.
