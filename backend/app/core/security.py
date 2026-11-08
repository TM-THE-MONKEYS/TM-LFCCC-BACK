from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import settings

# Precomputed bcrypt hash used only for timing-safe login when the user is missing.
# Password: "timing-safe-dummy-password-not-a-real-account"
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"timing-safe-dummy-password-not-a-real-account", bcrypt.gensalt()
)

_MAX_PASSWORD_BYTES = 72


def password_byte_length(password: str) -> int:
    return len(password.encode("utf-8"))


def assert_password_byte_limit(password: str) -> None:
    """Raise ValueError if password exceeds bcrypt's 72-byte limit."""
    if password_byte_length(password) > _MAX_PASSWORD_BYTES:
        raise ValueError("A senha não pode ultrapassar 72 bytes (limite do bcrypt).")


def hash_password(password: str) -> str:
    assert_password_byte_limit(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def verify_password_or_dummy(plain_password: str, hashed_password: str | None) -> bool:
    """Verify against the real hash, or a dummy hash when the user is missing (timing)."""
    target = hashed_password.encode("utf-8") if hashed_password else _DUMMY_PASSWORD_HASH
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), target)
    except ValueError:
        return False


def create_access_token(subject: str | Any) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "jti": str(uuid4()),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_value, algorithm="HS256")
    # PyJWT may return str or bytes depending on version/config.
    return token if isinstance(token, str) else token.decode("utf-8")


def decode_access_token(token: str) -> str | None:
    """Decode a JWT and return the subject if it is a valid access token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_value, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        sub: str | None = payload.get("sub")
        return sub
    except jwt.PyJWTError:
        return None


def decode_access_token_claims(token: str) -> dict[str, Any] | None:
    """Decode and return the full claims dict, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_value, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None
