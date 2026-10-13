"""Tokens opacos (sesiones y enlaces de un solo uso). Se guarda solo su SHA-256."""

from __future__ import annotations

import hashlib
import secrets


def new_token() -> str:
    return secrets.token_urlsafe(32)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def email_digest(email: str) -> str:
    return digest("email:" + normalize_email(email))
