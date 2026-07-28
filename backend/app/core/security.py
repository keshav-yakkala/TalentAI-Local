"""
TalentAI — Security Utilities
Password hashing (bcrypt) and JWT token management.

Rules:
- Passwords are hashed with bcrypt (work factor 12).
- JWT access tokens expire in ACCESS_TOKEN_EXPIRE_MINUTES.
- Refresh tokens expire in REFRESH_TOKEN_EXPIRE_DAYS.
- organization_id is NEVER resolved from token claims alone;
  always verify via DB membership query to prevent IDOR.
"""
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError, TokenExpiredError


# ── Password Hashing ─────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt (work factor 12)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT Tokens ────────────────────────────────────────────────────────────────


def _create_token(
    data: dict[str, Any],
    expires_delta: timedelta,
    token_type: str,
) -> str:
    payload = data.copy()
    now = datetime.now(UTC)
    payload.update(
        {
            "iat": now,
            "exp": now + expires_delta,
            "type": token_type,
        }
    )
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: UUID, email: str, role: str) -> str:
    """Create a short-lived access token."""
    return _create_token(
        data={"sub": str(user_id), "email": email, "role": role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: UUID) -> str:
    """Create a long-lived refresh token (contains only user_id)."""
    return _create_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises AuthenticationError on invalid token.
    Raises TokenExpiredError on expired token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError("Token has expired") from exc
        raise AuthenticationError("Invalid authentication token") from exc


def extract_user_id(token: str) -> UUID:
    """Convenience: decode token and return the user UUID."""
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Token missing subject claim")
    return UUID(sub)
