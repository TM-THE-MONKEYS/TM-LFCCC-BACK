from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.enums import DonationCategory, DonationDirection, UserRole
from app.exceptions import UnprocessableError
from app.models.user import User
from app.schemas.common import ListResponse, PaginationMeta, StandardResponse
from app.schemas.donation import DonationInput, DonationPatchInput, DonationResponse
from app.services.donation_service import DonationService

router = APIRouter()

_OPENAPI_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Não autenticado"},
    403: {"description": "Sem permissão"},
    404: {"description": "Não encontrado"},
    409: {"description": "Conflito"},
    422: {"description": "Validação inválida"},
}


def _parse_iso_dt(raw: str | None, *, end_of_day: bool = False) -> datetime | None:
    if raw is None or not raw.strip():
        return None
    value = raw.strip()
    try:
        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
            if end_of_day:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999000)
            return dt
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as exc:
        raise UnprocessableError(f"Data inválida: '{raw}'. Use YYYY-MM-DD ou ISO 8601.") from exc


@router.get(
    "",
    response_model=ListResponse[DonationResponse],
    summary="Listar doações",
    operation_id="list_donations",
    responses={401: _OPENAPI_ERRORS[401], 403: _OPENAPI_ERRORS[403], 422: _OPENAPI_ERRORS[422]},
)
def list_donations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    direction: DonationDirection | None = Query(default=None),
    category: DonationCategory | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    items, total = DonationService(db).list_filtered(
        skip=skip,
        limit=limit,
        direction=direction.value if direction else None,
        category=category.value if category else None,
        from_dt=_parse_iso_dt(from_),
        to_dt=_parse_iso_dt(to, end_of_day=True),
    )
    return ListResponse(
        message="Doações listadas com sucesso.",
        data=[DonationResponse.model_validate(d) for d in items],
        meta=PaginationMeta(total=total, skip=skip, limit=limit),
    )


@router.get(
    "/{donation_id}",
    response_model=StandardResponse[DonationResponse],
    summary="Detalhe da doação",
    operation_id="get_donation",
    responses=_OPENAPI_ERRORS,
)
def get_donation(
    donation_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return StandardResponse(
        message="Doação encontrada.",
        data=DonationResponse.model_validate(DonationService(db).get_by_id(str(donation_id))),
    )


@router.post(
    "",
    response_model=StandardResponse[DonationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar doação",
    operation_id="create_donation",
    responses=_OPENAPI_ERRORS,
)
def create_donation(
    data: DonationInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return StandardResponse(
        message="Doação registrada com sucesso.",
        data=DonationResponse.model_validate(DonationService(db).create(data)),
    )


@router.patch(
    "/{donation_id}",
    response_model=StandardResponse[DonationResponse],
    summary="Atualizar doação (parcial)",
    operation_id="patch_donation",
    responses=_OPENAPI_ERRORS,
)
def patch_donation(
    donation_id: UUID,
    data: DonationPatchInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return StandardResponse(
        message="Doação atualizada com sucesso.",
        data=DonationResponse.model_validate(DonationService(db).patch(str(donation_id), data)),
    )


@router.delete(
    "/{donation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir doação",
    operation_id="delete_donation",
    responses={
        401: _OPENAPI_ERRORS[401],
        403: _OPENAPI_ERRORS[403],
        404: _OPENAPI_ERRORS[404],
        422: _OPENAPI_ERRORS[422],
    },
)
def delete_donation(
    donation_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    DonationService(db).delete(str(donation_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
