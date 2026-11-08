from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.openapi_responses import OPENAPI_ERRORS
from app.core.logging import logger
from app.core.rate_limit import login_rate_limiter
from app.exceptions.domain import ForbiddenError, UnauthorizedError
from app.exceptions.handlers import error_response
from app.models.user import User
from app.schemas.common import StandardResponse
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService, normalize_email

router = APIRouter()


@router.post(
    "/login",
    response_model=StandardResponse[TokenResponse],
    summary="Autenticar e obter JWT",
    operation_id="login",
    responses={
        401: OPENAPI_ERRORS[401],
        422: OPENAPI_ERRORS[422],
        429: OPENAPI_ERRORS[429],
    },
)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    email_key = normalize_email(str(data.email))
    rate_key = f"{client_ip}:{email_key}"
    if not login_rate_limiter.is_allowed(rate_key):
        logger.warning("auth_login outcome=rate_limited client_ip=%s", client_ip)
        response = error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas de login. Aguarde um minuto e tente novamente.",
        )
        response.headers["Retry-After"] = "60"
        return response
    try:
        token = AuthService(db).login(data)
    except (UnauthorizedError, ForbiddenError):
        # No email/password in logs — IP only for abuse triage.
        logger.info("auth_login outcome=failure client_ip=%s", client_ip)
        raise
    logger.info("auth_login outcome=success client_ip=%s", client_ip)
    return StandardResponse(message="Login realizado com sucesso.", data=token)


@router.get(
    "/me",
    response_model=StandardResponse[UserResponse],
    summary="Usuário autenticado atual",
    operation_id="get_me",
    responses={401: OPENAPI_ERRORS[401]},
)
def me(current_user: User = Depends(get_current_user)):
    return StandardResponse(
        message="Usuário autenticado.",
        data=UserResponse.model_validate(current_user),
    )
