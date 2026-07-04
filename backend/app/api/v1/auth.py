from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import StandardResponse
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=StandardResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    user = AuthService(db).register(data)
    return StandardResponse(
        message="Usuário cadastrado com sucesso.",
        data=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=StandardResponse[TokenResponse])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    token = AuthService(db).login(data)
    return StandardResponse(message="Login realizado com sucesso.", data=token)


@router.get("/me", response_model=StandardResponse[UserResponse])
def me(current_user: User = Depends(get_current_user)):
    return StandardResponse(
        message="Usuário autenticado.",
        data=UserResponse.model_validate(current_user),
    )
