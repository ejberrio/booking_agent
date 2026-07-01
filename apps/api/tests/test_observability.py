from app.core.observability import init_sentry, setup_logging


def test_init_sentry_noop_without_dsn():
    # Sin DSN -> no-op (no lanza, devuelve False).
    assert init_sentry(None, "development") is False
    assert init_sentry("", "development") is False


def test_setup_logging_idempotent():
    import logging

    setup_logging("INFO")
    setup_logging("INFO")  # no debe duplicar handlers
    root = logging.getLogger()
    obs_handlers = [h for h in root.handlers if getattr(h, "_obs", False)]
    assert len(obs_handlers) == 1
