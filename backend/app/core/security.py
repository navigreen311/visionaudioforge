"""Security utilities: password hashing and JWT token management."""

import os
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings

# Bcrypt cost factor (12 ≈ 250 ms per hash on modern hardware).
BCRYPT_ROUNDS = 12

# bcrypt only reads the first 72 bytes of a password; anything past that is
# silently ignored by the algorithm itself. We truncate explicitly so a long
# passphrase hashes instead of raising, and so hash and verify agree.
BCRYPT_MAX_BYTES = 72

# NOTE: this used to go through passlib's CryptContext. passlib 1.7.4 probes
# `bcrypt.__about__.__version__`, which bcrypt 4.1+ removed, and its
# wrap-bug detection feeds an over-length password to the backend — which
# bcrypt 5 rejects with ValueError. The result was that hash_password() raised
# on every call. The `bcrypt` package is a direct dependency and produces the
# same `$2b$` hashes, so existing stored hashes keep verifying.

# JWT secret MUST come from environment — fail loudly if using the insecure default
_JWT_SECRET = os.environ.get("JWT_SECRET_KEY", settings.JWT_SECRET_KEY)
if _JWT_SECRET in ("change-me-jwt-secret", ""):
    import warnings

    warnings.warn(
        "JWT_SECRET_KEY is not set or uses the insecure default. "
        "Set the JWT_SECRET_KEY environment variable before deploying.",
        stacklevel=1,
    )

# Token expiry defaults
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_to_bcrypt_bytes(password), salt).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            _to_bcrypt_bytes(plain_password),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Malformed or non-bcrypt hash — never leak the difference between
        # "wrong password" and "corrupt record" to the caller.
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token (default 30 min expiry)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, _JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token (default 7 day expiry)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, _JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises HTTPException 401 on failure."""
    try:
        payload = jwt.decode(
            token,
            _JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )
