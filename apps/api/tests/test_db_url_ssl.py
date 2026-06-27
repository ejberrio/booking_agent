"""Normalización de DATABASE_URL para asyncpg/SSL (Neon)."""

from app.core.config import normalize_db_url


def test_neon_url_strips_sslmode_and_enables_ssl():
    url = "postgresql://user:pass@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    normalized, connect_args = normalize_db_url(url)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "sslmode" not in normalized
    assert "channel_binding" not in normalized
    assert connect_args == {"ssl": True}


def test_local_url_without_sslmode_has_no_ssl():
    url = "postgresql+asyncpg://booking:booking@localhost:5432/booking"
    normalized, connect_args = normalize_db_url(url)
    assert normalized == url
    assert connect_args == {}


def test_sslmode_disable_does_not_enable_ssl():
    url = "postgresql://u:p@host/db?sslmode=disable"
    normalized, connect_args = normalize_db_url(url)
    assert connect_args == {}
    assert "sslmode" not in normalized


def test_plain_postgres_scheme_is_upgraded_to_asyncpg():
    normalized, _ = normalize_db_url("postgres://u:p@host/db")
    assert normalized.startswith("postgresql+asyncpg://")
