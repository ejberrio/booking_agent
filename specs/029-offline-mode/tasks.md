# Tasks: Feature 029

- [X] T001 `account.channel_mode`, `channel.listing_url/ical_url` + migración `e5f6a7b8c9d1`
- [X] T002 `ManualChannelAdapter` y selección por cuenta (`require_ctx`, cron)
- [X] T003 `manual_service` (crear apartamento, siembra 365 noches, enlaces) y `ical_service` (lista blanca, parser, reservas/bloqueos/cancelaciones)
- [X] T004 Rutas `/manual`, `/manual/apartments`, `/manual/apartments/{id}/listings`, `/manual/ical/sync`; `channel_mode` en `/account`
- [X] T005 Escaneo diario con iCal para cuentas manuales; nota de "aplicar a mano" en el asistente
- [X] T006 Web: dos caminos en la cuenta vacía, formulario del apartamento, Ajustes → Modo sin conexión, aviso en Sugerencias, etiqueta en el menú (es/en/pt)
- [X] T007 Pruebas `test_offline_mode.py`
- [ ] T008 Staging, verificación del host, copia de Neon, producción, cerrar #146
