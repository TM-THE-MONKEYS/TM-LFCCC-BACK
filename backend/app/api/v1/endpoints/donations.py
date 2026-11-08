from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.datetime_parse import parse_iso_dt
from app.api.deps import get_db, require_role
from app.api.openapi_responses import OPENAPI_ERRORS
from app.core.enums import DonationCategory, DonationDirection, UserRole
from app.models.user import User
from app.schemas.common import ListResponse, PaginationMeta, StandardResponse
from app.schemas.donation import DonationInput, DonationPatchInput, DonationResponse
from app.services.donation_service import DonationService

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse[DonationResponse],
    summary="Listar doações",
    operation_id="list_donations",
    responses={401: OPENAPI_ERRORS[401], 403: OPENAPI_ERRORS[403], 422: OPENAPI_ERRORS[422]},
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
        from_dt=parse_iso_dt(from_),
        to_dt=parse_iso_dt(to, end_of_day=True),
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
    responses=OPENAPI_ERRORS,
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
    responses=OPENAPI_ERRORS,
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
    responses=OPENAPI_ERRORS,
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
        401: OPENAPI_ERRORS[401],
        403: OPENAPI_ERRORS[403],
        404: OPENAPI_ERRORS[404],
        422: OPENAPI_ERRORS[422],
    },
)
def delete_donation(
    donation_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    DonationService(db).delete(str(donation_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
