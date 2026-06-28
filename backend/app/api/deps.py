from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings

# get_db is defined once in database.py and re-exported here so routers and
# tests always reference the exact same function object (required for
# FastAPI dependency_overrides to work correctly).
from app.core.database import get_db  # noqa: F401 — re-export

from app.core.security import decode_access_token
from app.models.user import User


# ── Auth bearer scheme (auto_error=False so we can handle it ourselves) ───────

_bearer = HTTPBearer(auto_error=False)


def _resolve_user(token: str, db: Session) -> User:
    """Decode JWT and load the user, raising 401 if invalid."""
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )
    # Import here to avoid circular dependency at module load time
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Strict auth dependency — raises 401 when token is missing or invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
        )
    return _resolve_user(credentials.credentials, db)


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Auth dependency that respects AUTH_REQUIRED env.

    - When AUTH_REQUIRED=true  → behaves like get_current_user (raises 401 if missing/invalid).
    - When AUTH_REQUIRED=false → returns None if no token present; still validates when present.
    """
    if credentials is None:
        if settings.AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticação não fornecido.",
            )
        return None
    return _resolve_user(credentials.credentials, db)
