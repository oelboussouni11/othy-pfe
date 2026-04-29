from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False


def _ttl(token_type: TokenType) -> timedelta:
    if token_type == "access":
        return timedelta(minutes=settings.jwt_access_token_ttl_min)
    return timedelta(days=settings.jwt_refresh_token_ttl_days)


def create_token(subject: str, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + _ttl(token_type),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Decode + validate. Raises jwt.PyJWTError on any failure (expired, bad sig, wrong type)."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"expected token type {expected_type}, got {payload.get('type')}"
        )
    return payload
