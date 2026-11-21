from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.api.openapi_responses import OPENAPI_ERRORS
from app.core.enums import UserRole
from app.core.logging import logger
from app.core.rate_limit import password_change_rate_limiter
from app.exceptions.handlers import error_response
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import ListResponse, PaginationMeta, StandardResponse
from app.schemas.user import (
    PasswordChangeInput,
    PasswordResetInput,
    UserCreate,
    UserPatchInput,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse[UserResponse],
    summary="Listar usuários",
    operation_id="list_users",
    responses={401: OPENAPI_ERRORS[401], 403: OPENAPI_ERRORS[403]},
)
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    repo = UserRepository(db)
    total = repo.count()
    users = repo.list_all(skip=skip, limit=limit)
    return ListResponse(
        message="Usuários listados com sucesso.",
        data=[UserResponse.model_validate(u) for u in users],
        meta=PaginationMeta(total=total, skip=skip, limit=limit),
    )


@router.post(
    "",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
    operation_id="create_user",
    responses={
        401: OPENAPI_ERRORS[401],
        403: OPENAPI_ERRORS[403],
        409: OPENAPI_ERRORS[409],
        422: OPENAPI_ERRORS[422],
    },
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    user = AuthService(db).create_user(data)
    return StandardResponse(
        message="Usuário cadastrado com sucesso.",
        data=UserResponse.model_validate(user),
    )


# Declared before /{user_id}/... so "me" is never parsed as a UUID.
@router.post(
    "/me/password",
    response_model=StandardResponse[UserResponse],
    summary="Trocar a própria senha (exige a senha atual)",
    operation_id="change_own_password",
    responses={
        401: OPENAPI_ERRORS[401],
        422: OPENAPI_ERRORS[422],
        429: OPENAPI_ERRORS[429],
    },
)
def change_own_password(
    data: PasswordChangeInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not password_change_rate_limiter.is_allowed(current_user.id):
        logger.warning("user_password_change outcome=rate_limited user_id=%s", current_user.id)
        response = error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas de troca de senha. Aguarde um minuto e tente novamente.",
        )
        response.headers["Retry-After"] = "60"
        return response
    user = UserService(db).change_own_password(current_user, data)
    return StandardResponse(
        message="Senha alterada com sucesso.",
        data=UserResponse.model_validate(user),
    )


@router.patch(
    "/{user_id}",
    response_model=StandardResponse[UserResponse],
    summary="Atualizar usuário (nome, papel, ativo)",
    description=(
        "Parcial: campos omitidos ou null não mudam. 409 ao tentar desativar/rebaixar a "
        "própria conta ou o último administrador ativo. Desativar revoga o acesso na hora "
        "(tokens existentes passam a responder 401)."
    ),
    operation_id="patch_user",
    responses=OPENAPI_ERRORS,
)
def patch_user(
    user_id: UUID,
    data: UserPatchInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(UserRole.admin)),
):
    user = UserService(db).patch(str(user_id), data, actor=actor)
    return StandardResponse(
        message="Usuário atualizado com sucesso.",
        data=UserResponse.model_validate(user),
    )


@router.post(
    "/{user_id}/password",
    response_model=StandardResponse[UserResponse],
    summary="Redefinir senha de outro usuário (admin)",
    operation_id="reset_user_password",
    responses=OPENAPI_ERRORS,
)
def reset_user_password(
    user_id: UUID,
    data: PasswordResetInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(UserRole.admin)),
):
    user = UserService(db).reset_password(str(user_id), data, actor=actor)
    return StandardResponse(
        message="Senha redefinida com sucesso.",
        data=UserResponse.model_validate(user),
    )
