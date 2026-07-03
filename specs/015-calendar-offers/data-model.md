# Data Model: Feature 015 — Calendario con ofertas + registro de deals nativos

**UNA migración**: tabla nueva `native_deal` (`c9d0e1f2a3b4`, down `b7c8d9e0f1a2`). Ningún modelo existente cambia.

## NativeDeal (NUEVA — app/models/pricing.py)

| Campo | Tipo | Regla |
|---|---|---|
| id | PK | |
| channel | Enum ChannelKind (existente, `create_type=False` en la migración) | servicio restringe a booking/airbnb |
| name | String(120) | requerido, no vacío |
| discount_pct | Numeric(5,2) | 0 ≤ pct ≤ 100 |
| date_from | Date, **nullable** | NULL = abierto por la izquierda |
| date_to | Date, **nullable** | NULL = abierto por la derecha; si ambos definidos, date_from ≤ date_to |
| is_active | Boolean, default true | interruptor local |
| created_at / updated_at | TimestampMixin | |

Sin FKs (registro global de la cuenta; single-tenant, una propiedad). Sin vínculo con el Channel Manager.

### Semántica

- **"Siempre activo"** = `date_from IS NULL AND date_to IS NULL` (semanal/mensual de Airbnb).
- **Solape con `[first, last]`**: `(date_from IS NULL OR date_from <= last) AND (date_to IS NULL OR date_to >= first)`.
- **Solape de canal con `channels_scope`**: `scope is None` (todos) → solapa; si no, `channel.value in scope`.
- **Deal relevante para advertencia**: activo Y solapa fechas Y solapa canal.
- **Marcado en calendario**: día `d` marcado si existe deal activo con `(date_from IS NULL OR date_from <= d) AND (date_to IS NULL OR date_to >= d)` — computado en el cliente.

## Promotion (existente — sin cambios)

Su `preview` gana un warning derivado de NativeDeal (no persiste nada nuevo).

## Vistas derivadas (no persistidas, cliente)

- `nativeDealDates: Set<fecha>` y `dealsByDate: Map<fecha, NativeDeal[]>` — del `GET /pricing/native-deals` (solo activos) cruzado con el mes visible.
- `promosByDate: Map<fecha, PromotionView[]>` — del `GET /pricing/promotions` existente (status ≠ retired) cruzado por `first_night..last_night`.
