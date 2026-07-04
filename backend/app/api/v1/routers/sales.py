from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, optional_auth
from app.models.user import User
from app.schemas.common import ListResponse
from app.schemas.sale import SaleInput, SaleResponse
from app.services.sale_service import SaleService

router = APIRouter()


@router.get("", response_model=ListResponse[SaleResponse])
def list_sales(db: Session = Depends(get_db)):
    return ListResponse(data=[SaleResponse.model_validate(s) for s in SaleService(db).list_all()])


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    data: SaleInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return SaleResponse.model_validate(SaleService(db).create(data))
