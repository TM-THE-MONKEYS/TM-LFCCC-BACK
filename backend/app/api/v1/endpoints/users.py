from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import ListResponse, PaginationMeta, StandardResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse[UserResponse],
    summary="Listar usuários",
    operation_id="list_users",
)
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    users = UserRepository(db).list_all(skip=skip, limit=limit)
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
