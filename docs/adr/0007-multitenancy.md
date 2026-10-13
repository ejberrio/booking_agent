# ADR 0007 — Multicliente: cuentas aisladas en una base compartida

**Fecha**: 2026-10-10 · **Estado**: aceptado · **Feature**: 026 (issue #143, épica #156)

## Contexto

StayLever era una herramienta personal: una contraseña compartida, una sesión sin identidad,
una API sin autenticación propia (confiaba en la red privada de Railway) y casi toda la
información global. La fase comercial (épica #156) necesita varios anfitriones con 1–5
apartamentos, cada uno con sus datos y credenciales aislados. La constitución v1.1.0 añade el
principio VI: **aislamiento por cuenta, no negociable**.

## Decisión

1. **Una base compartida, `account_id` en todas las tablas del anfitrión** (mixin
   `AccountOwned`, 28 tablas, también las hijas de `unit_type`). Nada de esquemas ni bases por
   cliente (principio V).
2. **Filtro automático en el ORM** (`app/db/tenancy.py`): `do_orm_execute` añade
   `with_loader_criteria(account_id == cuenta)` a todo SELECT/UPDATE/DELETE (incluye
   `session.get`, relaciones y alias); `before_flush` rellena la cuenta de las filas nuevas y
   rechaza filas ajenas; **falla cerrado** (`TenantContextMissing`) si se tocan datos sin
   cuenta en la sesión. Verificado con SQLAlchemy 2.0.51 sobre SQLite y PostgreSQL 16.
3. **La cuenta sale solo de la sesión** (`app/core/context.py`: `current_identity` →
   `require_ctx`), de la clave del aviso entrante de Beds24, o del recorrido del cron. Nunca
   de un parámetro del navegador ni del LLM. `require_ctx` además responde 404 a cualquier
   `unit_type_id` ajeno antes de llegar a los servicios.
4. **Consultas entre cuentas acotadas**: la sesión de plataforma (`platform_session`) solo en
   el panel de administrador y el cron; las operaciones por tabla en `app/db/cross_account.py`
   (¿propiedad ya conectada a otra cuenta?, liberar el token de un teléfono). Una prueba
   estática falla si aparecen en otro módulo.
5. **Secretos por ámbito**: plataforma (IA, búsqueda, Firebase, correo, Google) vs. cuenta
   (Beds24); caché `(cuenta|None, nombre)`; los de cuenta nunca se resuelven "por defecto".
6. **Datos públicos compartidos**: eventos por ciudad (`event.city`, único `(city, dedup_key)`)
   y referencias de mercado por zona. El cron escanea cada ciudad una sola vez por corrida.
7. **Identidad en la API** (PR2): usuarios, Argon2id, sesiones opacas revocables (hash en BD),
   cookie `sl_session` en la web → `Authorization: Bearer` en el proxy. Correo con Resend y
   Google con PKCE (en Android, navegador del sistema + retorno a la app, APK 1.1.0).
8. **Entrega en 4 PRs desplegables**; el PR1 (este ADR) no cambia nada visible:
   `AUTH_MODE=legacy` resuelve toda petición a la cuenta nº 1 hasta activar las sesiones.

## Consecuencias

- Los servicios existentes casi no cambiaron: el aislamiento vive en la capa de datos.
- Un olvido de contexto produce un error, no una fuga de datos.
- Una propiedad de Beds24 solo puede pertenecer a una cuenta.
- Row Level Security de PostgreSQL queda como refuerzo futuro (las pruebas corren en SQLite).
- Los canales activos (`CHANNELS_ACTIVE`) y la oferta de promociones siguen siendo de
  configuración global hasta que haga falta configurarlos por cuenta.
