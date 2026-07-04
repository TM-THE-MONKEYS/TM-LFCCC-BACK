from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, optional_auth
from app.models.user import User
from app.schemas.common import ListResponse, StandardResponse
from app.schemas.sale import SaleInput, SaleResponse
from app.services.sale_service import SaleService

router = APIRouter()


@router.get("", response_model=ListResponse[SaleResponse])
def list_sales(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return ListResponse(
        message="Vendas listadas com sucesso.",
        data=[SaleResponse.model_validate(s) for s in SaleService(db).list_all(skip=skip, limit=limit)],
    )


@router.get("/{sale_id}", response_model=StandardResponse[SaleResponse])
def get_sale(sale_id: str, db: Session = Depends(get_db)):
    return StandardResponse(
        message="Venda encontrada.",
        data=SaleResponse.model_validate(SaleService(db).get_by_id(sale_id)),
    )


@router.post("", response_model=StandardResponse[SaleResponse], status_code=status.HTTP_201_CREATED)
def create_sale(
    data: SaleInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return StandardResponse(
        message="Venda registrada com sucesso.",
        data=SaleResponse.model_validate(SaleService(db).create(data)),
    )
