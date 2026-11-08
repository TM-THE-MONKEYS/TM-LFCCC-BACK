from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.rate_limit import login_rate_limiter
from app.models.user import User
from app.schemas.common import StandardResponse
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService, normalize_email

router = APIRouter()


@router.post("/login", response_model=StandardResponse[TokenResponse])
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    email_key = normalize_email(str(data.email))
    rate_key = f"{client_ip}:{email_key}"
    if not login_rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde um minuto e tente novamente.",
        )
    token = AuthService(db).login(data)
    return StandardResponse(message="Login realizado com sucesso.", data=token)


@router.get("/me", response_model=StandardResponse[UserResponse])
def me(current_user: User = Depends(get_current_user)):
    return StandardResponse(
        message="Usuário autenticado.",
        data=UserResponse.model_validate(current_user),
    )
