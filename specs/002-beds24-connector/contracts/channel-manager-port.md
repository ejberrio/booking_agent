# Contrato — Puerto provider-agnostic `ChannelManager`

Interfaz que todo Channel Manager debe implementar. Vive en `app/channels/base.py` como `Protocol` (tipado). El `sync_service` depende de esta interfaz, NO de Beds24.

## Interfaz

```python
class ChannelManager(Protocol):
    async def test_connection(self) -> ConnectionInfo: ...
    async def get_properties(self) -> list[RemoteProperty]: ...
    async def get_rates(
        self, room_external_id: str, date_from: date, date_to: date
    ) -> list[RemoteRate]: ...
    async def get_bookings(
        self, property_external_id: str, since: date | None = None
    ) -> list[RemoteBooking]: ...
    async def set_rate(
        self, room_external_id: str, day: date, price: Decimal
    ) -> WriteResult: ...
    async def set_rate_range(
        self, room_external_id: str, date_from: date, date_to: date, price: Decimal
    ) -> WriteResult: ...
```

## Garantías de comportamiento (cualquier implementación)

- **C1 — Sin fugas del proveedor**: los métodos devuelven DTOs neutrales (`Remote*`, `WriteResult`, `ConnectionInfo`); nada propietario de Beds24 cruza la frontera.
- **C2 — Errores tipados**: fallos se expresan con excepciones del módulo `app/channels/errors.py` (`AuthError`, `RateLimited`, `ChannelError`, `WriteUnverified`), no con detalles HTTP crudos.
- **C3 — Escritura verificada**: `set_rate`/`set_rate_range` devuelven `WriteResult.verified=True` solo si una relectura confirma el valor; si no se pudo verificar, `verified=False` (y el `sync_service` abre `SyncIssue`).
- **C4 — Idempotencia**: fijar el mismo precio dos veces produce el mismo estado, sin error.
- **C5 — Rate limiting**: ante límite del proveedor, la implementación reintenta con backoff; si agota reintentos, lanza `RateLimited`.
- **C6 — Secretos**: ninguna credencial aparece en mensajes de error, repr de DTOs ni logs.

## Contrato de `sync_service` (orquestación, depende del puerto)

| Operación | Comportamiento |
|-----------|----------------|
| `import_remote()` | `get_properties` + `get_rates` + `get_bookings` → upsert en modelos 001 (mapeando `external_ref`); baseline de precios sin auditar; abre `SyncIssue` ante discrepancias de precio (no sobrescribe). Registra `SyncRun(import)`. |
| `publish_price(unit_type, day/range, price)` | El host ya fijó el precio local (auditado). Llama `set_rate`/`set_rate_range`; si `verified=False`, abre `SyncIssue(write_unverified)`. Registra `SyncRun(publish)`. |
| `reconcile()` | Compara local vs remoto; reservas/disponibilidad remotas → local; discrepancias de precio → `SyncIssue`, nunca overwrite silencioso. |

## Contrato de pruebas (qué verifican los tests)

| Test | Verifica |
|------|----------|
| `test_beds24_adapter::test_get_properties_maps_dtos` | parsea respuesta V1 → RemoteProperty/RemoteRoom (C1) |
| `test_beds24_adapter::test_set_rate_verifies` | tras escribir, relee y marca `verified=True` (C3) |
| `test_beds24_adapter::test_auth_error_raises` | credenciales inválidas → `AuthError` (C2) |
| `test_beds24_adapter::test_rate_limit_backoff` | respuesta de rate limit → reintenta y/o `RateLimited` (C5) |
| `test_beds24_adapter::test_no_secret_in_errors` | la apiKey no aparece en el mensaje de error (C6) |
| `test_sync_service::test_import_upserts_without_audit` | import de baseline no crea `PriceChangeLog` |
| `test_sync_service::test_price_discrepancy_opens_issue` | divergencia → `SyncIssue`, sin overwrite (C0 reconciliación) |
| `test_sync_service::test_publish_unverified_opens_issue` | `verified=False` → `SyncIssue(write_unverified)` |
