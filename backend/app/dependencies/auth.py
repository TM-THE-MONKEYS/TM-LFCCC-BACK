"""Dependências de autenticação e banco de dados.

Funções injetáveis usadas pelos handlers de rota via Depends().
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db  # noqa: F401 — re-exported for dependency_overrides compat
from app.core.security import decode_access_token
from app.models.user import User

# ── Esquema Bearer (auto_error=False para tratarmos o erro manualmente) ─────────

_bearer = HTTPBearer(auto_error=False)


def _resolve_user(token: str, db: Session) -> User:
    """Decode JWT and load the user, raising 401 if invalid."""
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )
    # Import adiado para evitar dependência circular na carga do módulo
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
