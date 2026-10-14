# Tasks: Uso y límites de IA por cuenta (Feature 027)

- [X] T001 Config: `ai_prices`, `ai_chat_limit_month=300`, `ai_search_limit_day=5`, `ai_timezone`
- [X] T002 Modelo `AIUsage` + columnas de límites en `account` + migración `d4e5f6a7b8c0` (probada en PG)
- [X] T003 [US1] `LLMResponse.usage` en `LiteLLMClient`; `usage_service` (record, costo, totales); `MeteredLLM`, `MeteredSearch`
- [X] T004 [US2] Chat: comprobar límite (excepto con acción pendiente), contar el mensaje, medir con `MeteredLLM`; `quota` en la respuesta
- [X] T005 [US3] `scan_daily`: medir y limitar por cuenta; omitidas en el detalle de la corrida
- [X] T006 [US4] Admin: `GET /admin/usage`, `PATCH /admin/accounts/{id}/limits`; host: `GET /account/usage`
- [X] T007 Web: aviso/límite en el chat, tarjeta "Uso del asistente" en Ajustes, sección "Uso de IA" en Administración (es/en/pt)
- [X] T008 Tests `test_ai_usage.py`; ajustar `test_scan_multi` y pruebas del chat
- [ ] T009 Docs (`docs/operations.md`, `docs/accounts.md`), CI, staging, verificación del host, copia de Neon, producción, cerrar #144
