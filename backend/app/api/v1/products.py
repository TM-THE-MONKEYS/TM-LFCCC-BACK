from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, optional_auth
from app.models.user import User
from app.schemas.common import ListResponse, StandardResponse
from app.schemas.product import ProductInput, ProductResponse, StockPatchInput
from app.services.product_service import ProductService

router = APIRouter()


@router.get("", response_model=ListResponse[ProductResponse])
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return ListResponse(
        message="Produtos listados com sucesso.",
        data=[ProductResponse.model_validate(p) for p in ProductService(db).list_all(skip=skip, limit=limit)],
    )


@router.get("/{product_id}", response_model=StandardResponse[ProductResponse])
def get_product(product_id: str, db: Session = Depends(get_db)):
    return StandardResponse(
        message="Produto encontrado.",
        data=ProductResponse.model_validate(ProductService(db).get_by_id(product_id)),
    )


@router.post("", response_model=StandardResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return StandardResponse(
        message="Produto criado com sucesso.",
        data=ProductResponse.model_validate(ProductService(db).create(data)),
    )


@router.put("/{product_id}", response_model=StandardResponse[ProductResponse])
def update_product(
    product_id: str,
    data: ProductInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return StandardResponse(
        message="Produto atualizado com sucesso.",
        data=ProductResponse.model_validate(ProductService(db).update(product_id, data)),
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    ProductService(db).delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{product_id}/stock", response_model=StandardResponse[ProductResponse])
def patch_stock(
    product_id: str,
    data: StockPatchInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return StandardResponse(
        message="Estoque atualizado com sucesso.",
        data=ProductResponse.model_validate(ProductService(db).patch_stock(product_id, data.delta)),
    )


@router.post("/{product_id}/image", response_model=StandardResponse[ProductResponse])
def upload_product_image(
    product_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return StandardResponse(
        message="Imagem enviada com sucesso.",
        data=ProductResponse.model_validate(ProductService(db).upload_image(product_id, file)),
    )
