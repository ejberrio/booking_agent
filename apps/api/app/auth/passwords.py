"""Contraseñas con Argon2id (feature 026). Nunca se guardan ni se registran en claro."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # perfil RFC 9106 "low memory": t=3, m=64 MiB, p=4

MIN_LENGTH = 10
# Lista corta de las más usadas (en minúsculas); la longitud mínima ya descarta casi todas.
_COMMON = {
    "1234567890", "12345678910", "123456789a", "qwertyuiop", "contraseña", "contrasena1",
    "password12", "password123", "iloveyou12", "staylever1", "staylever12", "abcdefghij",
    "0123456789", "1111111111", "aaaaaaaaaa", "qwerty1234", "colombia123", "medellin123",
}


class WeakPassword(ValueError):
    pass


def check_policy(password: str) -> None:
    if len(password or "") < MIN_LENGTH:
        raise WeakPassword(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres")
    if password.lower() in _COMMON or len(set(password)) < 4:
        raise WeakPassword("Esa contraseña es demasiado común; elige otra")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored: str | None, password: str) -> bool:
    if not stored:
        return False
    try:
        return _hasher.verify(stored, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored: str) -> bool:
    return _hasher.check_needs_rehash(stored)
