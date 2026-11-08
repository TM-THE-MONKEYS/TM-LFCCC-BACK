import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password_or_dummy,
)
from app.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, TokenResponse, UserCreate


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, db: Session) -> None:
        self._repo = UserRepository(db)
        self._db = db

    def create_user(self, data: UserCreate) -> User:
        email = normalize_email(data.email)
        if self._repo.get_by_email(email) is not None:
            raise ConflictError(f"Já existe um usuário com o e-mail '{email}'.")
        user = User(
            id=str(uuid.uuid4()),
            name=data.name,
            email=email,
            password_hash=hash_password(data.password),
            role=data.role.value if isinstance(data.role, UserRole) else str(data.role),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        self._repo.create(user)
        return user

    def login(self, data: LoginRequest) -> TokenResponse:
        email = normalize_email(str(data.email))
        user = self._repo.get_by_email(email)
        # Always run bcrypt (dummy hash if user missing) to reduce timing oracle.
        password_ok = verify_password_or_dummy(
            data.password, user.password_hash if user is not None else None
        )
        if user is None or not password_ok:
            raise UnauthorizedError("E-mail ou senha inválidos.")
        if not user.is_active:
            raise ForbiddenError("Conta desativada.")
        token = create_access_token(user.id)
        return TokenResponse(access_token=token, token_type="bearer")
