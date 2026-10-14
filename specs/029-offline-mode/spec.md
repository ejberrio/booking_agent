# Feature Specification: Modo sin conexión (apartamento manual)

**Branch**: `029-offline-mode` · **Created**: 2026-10-14 · **Input**: issue #146 (Feature 029, épica #156)

## Decisiones del host (2026-10-14)
1. Ocupación: **calendario iCal** de exportación de Airbnb/Booking (solo lectura) **+ marcar noches a mano**.
2. Al aplicar una sugerencia: **StayLever registra el nuevo precio** (las siguientes sugerencias parten de él), la marca aplicada y muestra **enlaces** al calendario de Airbnb y a la extranet de Booking para copiarlo.
3. El asistente **sí propone cambios** en modo sin conexión, sobre el registro de StayLever, recordando aplicarlos a mano (nada se publica).

## User Stories
1. (P1) Cuenta nueva sin channel manager elige "Usar sin conexión" y crea su apartamento (nombre, ciudad, moneda, precio entre semana y de viernes/sábado, enlaces de anuncio e iCal): StayLever siembra 365 noches y empieza a sugerir.
2. (P1) Las noches ocupadas llegan del iCal (reservas sin nombre del huésped; bloqueos "Not available") en el escaneo diario o con "Sincronizar calendarios ahora"; las reservas que desaparecen se cancelan.
3. (P1) Sugerencias, calendario (bloquear/abrir), precios en bloque y el asistente funcionan igual, sin publicar; la app recuerda aplicar a mano con enlaces.
4. (P2) Avisos al celular de sugerencias nuevas (como hoy, por cuenta).

## Requirements
- FR-001 `account.channel_mode` = connected | manual; adaptador `ManualChannelAdapter` (la base es la verdad) para cuentas manuales; nunca se habla con un Channel Manager.
- FR-002 Hasta 5 apartamentos sin conexión por cuenta; una cuenta conectada no pasa a manual.
- FR-003 iCal: solo https de dominios conocidos (Airbnb, Booking, Vrbo, Google Calendar), sin redirecciones, ≤ 1 MB, 15 s; el enlace completo no se devuelve ni se registra en logs.
- FR-004 Escaneo diario: para cuentas manuales, iCal antes de sugerir.
- FR-005 Respuestas del asistente y pantalla de Sugerencias avisan que hay que aplicar a mano.
- FR-006 Pasar a conectado más adelante (F1) conserva el historial (fuera de alcance aquí).
