# Tasks: Feature 032

- [X] T001 `services/bulk_service.py`: plan/aplicación de cambio de precio por noche (set/percent/amount) y de descuento por tramos (plan_promo + offer_promotion_service)
- [X] T002 Herramientas: `propose_price_change`, `get_suggestions` mejorada, `propose_apply_suggestions`, `propose_reject_suggestions`, `propose_discount`; alias y legacy ocultas
- [X] T003 Vista previa estructurada común (`kind`, `rows`, `totals`, `warnings`, `currency`)
- [X] T004 Orquestador: lecturas en paralelo, una sola propuesta, MAX_STEPS 10
- [X] T005 `POST /chat/actions/{id}/confirm|cancel` + `pending_action` en respuestas y en la conversación
- [X] T006 Prompt reescrito (regla de lote, fin de semana [4,5], multicanal)
- [X] T007 Web: tabla de la propuesta y botones deterministas (es/en/pt)
- [X] T008 Pruebas (`test_agent_bulk.py`) y ajustes de pruebas existentes
- [ ] T009 Staging, verificación del host, copia de Neon, producción, cerrar #172
