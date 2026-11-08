from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.api.openapi_responses import OPENAPI_ERRORS
from app.core.enums import ProductCategory, UserRole
from app.models.user import User
from app.schemas.common import ListResponse, PaginationMeta, StandardResponse
from app.schemas.product import (
    ProductInput,
    ProductPatchInput,
    ProductPublicResponse,
    ProductResponse,
    StockPatchInput,
)
from app.services.product_service import ProductService

router = APIRouter()


@router.get(
    "",
    response_model=ListResponse[ProductPublicResponse],
    summary="Listar produtos (catálogo público)",
    operation_id="list_products",
    responses={422: OPENAPI_ERRORS[422]},
)
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    q: str | None = Query(default=None, description="Busca em nome/SKU/descrição"),
    category: ProductCategory | None = Query(default=None),
    isActive: bool | None = Query(
        default=True,
        description="Default true — catálogo público oculta inativos",
    ),
    inStock: bool | None = Query(default=None),
    sort: str | None = Query(
        default=None,
        description="Campo de ordenação; prefixo '-' para desc (name,sku,price,quantity,created_at,updated_at)",
    ),
    db: Session = Depends(get_db),
):
    """Catálogo público — sem costPrice. Inativos ocultos por default."""
    items, total = ProductService(db).list_filtered(
        skip=skip,
        limit=limit,
        q=q,
        category=category.value if category else None,
        is_active=isActive,
        in_stock=inStock,
        sort=sort,
    )
    return ListResponse(
        message="Produtos listados com sucesso.",
        data=[ProductPublicResponse.model_validate(p) for p in items],
        meta=PaginationMeta(total=total, skip=skip, limit=limit),
    )


@router.get(
    "/{product_id}/manage",
    response_model=StandardResponse[ProductResponse],
    summary="Detalhe admin com costPrice",
    operation_id="get_product_manage",
    responses=OPENAPI_ERRORS,
)
def get_product_manage(
    product_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Detalhe interno (admin) — inclui costPrice; permite inativos."""
    return StandardResponse(
        message="Produto encontrado.",
        data=ProductResponse.model_validate(ProductService(db).get_by_id(str(product_id))),
    )


@router.get(
    "/{product_id}",
    response_model=StandardResponse[ProductPublicResponse],
    summary="Detalhe público do produto",
    operation_id="get_product",
    responses={404: OPENAPI_ERRORS[404], 422: OPENAPI_ERRORS[422]},
)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Detalhe público — sem costPrice; inativos → 404."""
    return StandardResponse(
        message="Produto encontrado.",
        data=ProductPublicResponse.model_validate(
            ProductService(db).get_public_by_id(str(product_id))
        ),
    )


@router.post(
    "",
    response_model=StandardResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Criar produto",
    operation_id="create_product",
    responses=OPENAPI_ERRORS,
)
def create_product(
    data: ProductInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return StandardResponse(
        message="Produto criado com sucesso.",
        data=ProductResponse.model_validate(ProductService(db).create(data)),
    )


@router.patch(
    "/{product_id}",
    response_model=StandardResponse[ProductResponse],
    summary="Atualizar produto (parcial; sem quantity)",
    operation_id="patch_product",
    responses=OPENAPI_ERRORS,
)
def patch_product(
    product_id: UUID,
    data: ProductPatchInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return StandardResponse(
        message="Produto atualizado com sucesso.",
        data=ProductResponse.model_validate(ProductService(db).patch(str(product_id), data)),
    )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete produto (isActive=false)",
    operation_id="delete_product",
    responses={
        401: OPENAPI_ERRORS[401],
        403: OPENAPI_ERRORS[403],
        404: OPENAPI_ERRORS[404],
        422: OPENAPI_ERRORS[422],
    },
)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    ProductService(db).soft_delete(str(product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{product_id}/stock",
    response_model=StandardResponse[ProductPublicResponse | ProductResponse],
    summary="Ajustar estoque (delta)",
    operation_id="patch_product_stock",
    responses=OPENAPI_ERRORS,
)
def patch_stock(
    product_id: UUID,
    data: StockPatchInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    product = ProductService(db).patch_stock(str(product_id), data.delta)
    # Operator: ProductPublicResponse (sem costPrice). Admin: ProductResponse.
    if current_user.role == UserRole.admin.value:
        payload: ProductPublicResponse | ProductResponse = ProductResponse.model_validate(product)
    else:
        payload = ProductPublicResponse.model_validate(product)
    return StandardResponse(message="Estoque atualizado com sucesso.", data=payload)


@router.post(
    "/{product_id}/image",
    response_model=StandardResponse[ProductResponse],
    summary="Upload de imagem do produto",
    operation_id="upload_product_image",
    responses=OPENAPI_ERRORS,
)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    product = await ProductService(db).upload_image(str(product_id), file)
    return StandardResponse(
        message="Imagem enviada com sucesso.",
        data=ProductResponse.model_validate(product),
    )
