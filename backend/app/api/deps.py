from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# get_db is defined once in database.py and re-exported here so routers and
# tests always reference the exact same function object (required for
# FastAPI dependency_overrides to work correctly).
from app.core.database import get_db  # noqa: F401 — re-export
from app.core.enums import UserRole
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
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Strict auth dependency — raises 401 when token is missing or invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
        )
    return _resolve_user(credentials.credentials, db)


def require_role(*roles: UserRole | str) -> Callable[..., User]:
    """Dependency factory that enforces the authenticated user has one of the roles."""
    allowed = {r.value if isinstance(r, UserRole) else str(r) for r in roles}

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação.",
            )
        return current_user

    return _checker
