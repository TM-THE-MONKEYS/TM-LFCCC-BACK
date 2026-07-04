import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings, _BACKEND_DIR
from app.exceptions import ConflictError, InsufficientStockError, NotFoundError, UnprocessableError
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductInput

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

_UPLOAD_BASE = (
    Path(settings.UPLOAD_DIR)
    if Path(settings.UPLOAD_DIR).is_absolute()
    else _BACKEND_DIR / settings.UPLOAD_DIR
)


class ProductService:
    def __init__(self, db: Session) -> None:
        self._repo = ProductRepository(db)
        self._db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        return self._repo.get_all(skip=skip, limit=limit)

    def get_by_id(self, product_id: str) -> Product:
        product = self._repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"Produto com id '{product_id}' não encontrado.")
        return product

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, data: ProductInput) -> Product:
        if self._repo.get_by_sku(data.sku) is not None:
            raise ConflictError(f"Já existe um produto com o SKU '{data.sku}'.")
        now = datetime.now(timezone.utc)
        product = Product(
            id=str(uuid.uuid4()),
            sku=data.sku,
            name=data.name,
            description=data.description,
            category=data.category.value,
            sizes=data.sizes,
            colors=data.colors,
            price=data.price,
            promo_price=data.promo_price,
            cost_price=data.cost_price,
            quantity=data.quantity,
            image_url=data.image_url,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._repo.create(product)
        self._db.commit()
        self._db.refresh(product)
        return product

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, product_id: str, data: ProductInput) -> Product:
        product = self.get_by_id(product_id)
        if data.sku != product.sku and self._repo.get_by_sku(data.sku) is not None:
            raise ConflictError(f"Já existe um produto com o SKU '{data.sku}'.")
        product.sku = data.sku
        product.name = data.name
        product.description = data.description
        product.category = data.category.value
        product.sizes = data.sizes
        product.colors = data.colors
        product.price = data.price
        product.promo_price = data.promo_price
        product.cost_price = data.cost_price
        product.quantity = data.quantity
        if data.image_url is not None:
            product.image_url = data.image_url
        product.updated_at = datetime.now(timezone.utc)
        self._repo.update(product)
        self._db.commit()
        self._db.refresh(product)
        return product

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, product_id: str) -> None:
        product = self.get_by_id(product_id)
        self._repo.delete(product)
        self._db.commit()

    # ── Stock patch ───────────────────────────────────────────────────────────

    def patch_stock(self, product_id: str, delta: int) -> Product:
        product = self.get_by_id(product_id)
        if delta < 0 and product.quantity + delta < 0:
            raise InsufficientStockError(
                f"Estoque insuficiente para ajuste. "
                f"Disponível: {product.quantity}, ajuste solicitado: {delta}."
            )
        product.updated_at = datetime.now(timezone.utc)
        updated = self._repo.update_stock(product, delta)
        self._db.commit()
        self._db.refresh(updated)
        return updated

    # ── Image upload ──────────────────────────────────────────────────────────

    async def upload_image(self, product_id: str, file: UploadFile) -> Product:
        product = self.get_by_id(product_id)

        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            raise UnprocessableError("Tipo de arquivo não permitido. Use: jpeg, png ou webp.")

        contents = await file.read()
        if len(contents) > _MAX_IMAGE_BYTES:
            raise UnprocessableError("Arquivo muito grande. Tamanho máximo: 5 MB.")

        ext = file.content_type.split("/")[-1].replace("jpeg", "jpg")
        filename = f"{uuid.uuid4()}.{ext}"

        upload_dir = _UPLOAD_BASE / "products"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename

        with open(file_path, "wb") as f:
            f.write(contents)

        product.image_url = f"{settings.PUBLIC_BASE_URL}/uploads/products/{filename}"
        product.updated_at = datetime.now(timezone.utc)
        self._repo.update(product)
        self._db.commit()
        self._db.refresh(product)
        return product

