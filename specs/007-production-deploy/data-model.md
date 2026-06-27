# Data Model — Despliegue (Railway + Neon)

Esta feature es de **infraestructura/operación**: **no introduce nuevas entidades persistentes ni cambios de esquema**. La base de datos es la ya definida en features 001–006 (propiedades, unidades, precios, reservas, sugerencias, auditoría, etc.), ahora alojada en Neon.

## Sin migraciones nuevas

- No se crean ni alteran tablas. Las migraciones existentes se aplican tal cual en Neon mediante `alembic upgrade head` al desplegar.
- La única lógica de datos tocada es la **conexión** (normalización de URL + SSL), no el modelo.

## "Entidades" de configuración (no persistentes)

Para trazabilidad de los requisitos, los conceptos que esta feature configura (detallados en `contracts/environment.md`):

| Concepto | Descripción | Dónde vive |
|----------|-------------|------------|
| Servicio `web` | Next.js público; sirve UI y proxy a la API | Railway |
| Servicio `api` | FastAPI privado; lógica y datos | Railway (red interna) |
| Servicio `scan` | Cron diario; ejecuta `scan_daily` | Railway |
| Base de datos | Postgres gestionado, SSL | Neon |
| Configuración de entorno | Variables (secretas y públicas) por servicio | Railway service variables |

## Invariantes de datos preservadas

- La auditoría y reversibilidad de precios (Constitución III) no cambian.
- La fuente de verdad externa es Beds24; la DB es reconstruible vía `POST /sync/import` (estrategia de recuperación v1).
