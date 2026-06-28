import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, TokenResponse, UserCreate


class AuthService:
    def __init__(self, db: Session) -> None:
        self._repo = UserRepository(db)
        self._db = db

    def register(self, data: UserCreate) -> User:
        if self._repo.get_by_email(data.email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um usuário com o e-mail '{data.email}'.",
            )
        user = User(
            id=str(uuid.uuid4()),
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self._repo.create(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self._repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha inválidos.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conta desativada.",
            )
        token = create_access_token(user.id)
        return TokenResponse(access_token=token, token_type="bearer")
