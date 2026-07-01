"""Backup lógico portable de la base (pg_dump) con retención simple.

Neon ya provee backups automáticos + restauración a un punto en el tiempo a
nivel de plataforma; este script añade una copia lógica *fuera* de Neon que el
operador puede guardar donde quiera y usar para restaurar en cualquier Postgres.

Los datos de precios/disponibilidad/reservas son re-importables desde Beds24
(fuente de verdad); lo que este backup preserva de forma irremplazable es el
rastro de auditoría (decisiones del agente, promociones, cambios de
disponibilidad, incidencias de sincronización, escaneos de inteligencia).

Uso:
    uv run python -m scripts.backup_db                 # dump + poda por retención
    BACKUP_DIR=/ruta uv run python -m scripts.backup_db
    BACKUP_RETENTION=14 uv run python -m scripts.backup_db

Restauración (probada, ver docs/operations.md):
    createdb destino
    pg_restore --clean --if-exists --no-owner -d "$DATABASE_URL" backups/booking-YYYYMMDDTHHMMSSZ.dump
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings

RETENTION = int(os.environ.get("BACKUP_RETENTION", "7"))
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "backups"))
PREFIX = "booking-"
SUFFIX = ".dump"


def _libpq_url() -> str:
    """URL para pg_dump (libpq): sin el driver asyncpg de SQLAlchemy.

    En Railway el DATABASE_URL llega por variable de entorno; se prefiere sobre
    el valor por defecto de settings para no depender de la ubicación del .env.
    """
    url = os.environ.get("DATABASE_URL") or settings.database_url
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _prune() -> list[Path]:
    """Conserva los RETENTION backups más recientes; borra el resto."""
    backups = sorted(BACKUP_DIR.glob(f"{PREFIX}*{SUFFIX}"))
    stale = backups[:-RETENTION] if RETENTION > 0 else []
    for old in stale:
        old.unlink()
    return stale


def main() -> int:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = BACKUP_DIR / f"{PREFIX}{stamp}{SUFFIX}"

    # -Fc: formato custom (comprimido, restaurable con pg_restore selectivo).
    result = subprocess.run(
        ["pg_dump", "--no-owner", "--no-privileges", "-Fc", "-f", str(out), _libpq_url()],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"backup_db: FALLÓ pg_dump\n{result.stderr}", file=sys.stderr)
        return result.returncode

    size_kb = out.stat().st_size / 1024
    pruned = _prune()
    kept = len(sorted(BACKUP_DIR.glob(f"{PREFIX}*{SUFFIX}")))
    print(
        f"backup_db: OK {out.name} ({size_kb:.1f} KB) · "
        f"retención={RETENTION} conservados={kept} podados={len(pruned)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
