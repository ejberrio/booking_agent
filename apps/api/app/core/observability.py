"""Observabilidad: init de Sentry (no-op sin DSN) y configuración de logging.

Sin secretos ni PII: send_default_pii=False y no se adjuntan cuerpos de request.
"""

from __future__ import annotations

import logging
import sys


def init_sentry(dsn: str | None, environment: str, release: str | None = None) -> bool:
    """Inicializa Sentry si hay DSN. Devuelve True si se activó, False si es no-op.

    No falla nunca por la observabilidad (best-effort).
    """
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=0.0,  # v1: solo errores
            send_default_pii=False,  # sin PII/secretos
        )
        return True
    except Exception:  # pragma: no cover - nunca romper el arranque por Sentry
        logging.getLogger("observability").warning("No se pudo iniciar Sentry", exc_info=True)
        return False


def setup_logging(level: str = "INFO") -> None:
    """Configura logging a stdout (lo recoge el proveedor de hosting)."""
    lvl = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)
    # Evita duplicar handlers si se llama más de una vez.
    if not any(getattr(h, "_obs", False) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler._obs = True  # type: ignore[attr-defined]
        root.addHandler(handler)
