from typing import Optional

from fastapi import APIRouter, Depends, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, optional_auth
from app.models.user import User
from app.schemas.common import ListResponse
from app.schemas.product import ProductInput, ProductResponse, StockPatchInput
from app.services.product_service import ProductService

router = APIRouter()


@router.get("", response_model=ListResponse[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return ListResponse(
        data=[ProductResponse.model_validate(p) for p in ProductService(db).list_all()]
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    return ProductResponse.model_validate(ProductService(db).get_by_id(product_id))


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return ProductResponse.model_validate(ProductService(db).create(data))


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    data: ProductInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return ProductResponse.model_validate(ProductService(db).update(product_id, data))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    ProductService(db).delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{product_id}/stock", response_model=ProductResponse)
def patch_stock(
    product_id: str,
    data: StockPatchInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return ProductResponse.model_validate(ProductService(db).patch_stock(product_id, data.delta))


@router.post("/{product_id}/image", response_model=ProductResponse)
async def upload_image(
    product_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return ProductResponse.model_validate(await ProductService(db).upload_image(product_id, file))
