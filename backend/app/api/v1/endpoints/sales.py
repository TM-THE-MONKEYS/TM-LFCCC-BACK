from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.datetime_parse import parse_iso_dt
from app.api.deps import get_current_user, get_db, require_role
from app.api.openapi_responses import OPENAPI_ERRORS
from app.core.enums import PaymentMethod, UserRole
from app.models.user import User
from app.schemas.common import ListResponse, PaginationMeta, StandardResponse
from app.schemas.sale import SaleInput, SaleResponse
from app.services.sale_service import SaleService

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse[SaleResponse],
    summary="Listar vendas",
    operation_id="list_sales",
    responses={401: OPENAPI_ERRORS[401], 422: OPENAPI_ERRORS[422]},
)
def list_sales(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    from_: str | None = Query(default=None, alias="from", description="YYYY-MM-DD ou ISO"),
    to: str | None = Query(default=None, description="YYYY-MM-DD ou ISO"),
    paymentMethod: PaymentMethod | None = Query(default=None),
    productId: UUID | None = Query(default=None),
    includeCancelled: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = SaleService(db).list_filtered(
        skip=skip,
        limit=limit,
        from_dt=parse_iso_dt(from_),
        to_dt=parse_iso_dt(to, end_of_day=True),
        payment_method=paymentMethod.value if paymentMethod else None,
        product_id=str(productId) if productId else None,
        include_cancelled=includeCancelled,
    )
    return ListResponse(
        message="Vendas listadas com sucesso.",
        data=[SaleResponse.model_validate(s) for s in items],
        meta=PaginationMeta(total=total, skip=skip, limit=limit),
    )


@router.get(
    "/{sale_id}",
    response_model=StandardResponse[SaleResponse],
    summary="Detalhe da venda",
    operation_id="get_sale",
    responses=OPENAPI_ERRORS,
)
def get_sale(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return StandardResponse(
        message="Venda encontrada.",
        data=SaleResponse.model_validate(SaleService(db).get_by_id(str(sale_id))),
    )


@router.post(
    "",
    response_model=StandardResponse[SaleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar venda",
    operation_id="create_sale",
    responses=OPENAPI_ERRORS,
)
def create_sale(
    data: SaleInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    return StandardResponse(
        message="Venda registrada com sucesso.",
        data=SaleResponse.model_validate(
            SaleService(db).create(data, actor_role=current_user.role)
        ),
    )


@router.post(
    "/{sale_id}/cancel",
    response_model=StandardResponse[SaleResponse],
    summary="Cancelar/estornar venda e restaurar estoque",
    operation_id="cancel_sale",
    responses=OPENAPI_ERRORS,
)
def cancel_sale(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return StandardResponse(
        message="Venda cancelada e estoque restaurado.",
        data=SaleResponse.model_validate(SaleService(db).cancel(str(sale_id))),
    )
