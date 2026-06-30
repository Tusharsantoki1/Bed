"""Password hashing (bcrypt) and JWT access/refresh token helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from ..config import settings

# bcrypt has a hard 72-byte limit on the input password.
_BCRYPT_MAX_BYTES = 72


# --- Passwords -------------------------------------------------------------

def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT -------------------------------------------------------------------

def _create_token(subject: str | int, token_type: str, expires_delta: timedelta,
                  extra: Optional[dict[str, Any]] = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, role: str, company_id: Optional[int]) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra={"role": role, "company_id": company_id},
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises jwt.PyJWTError on any problem."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
