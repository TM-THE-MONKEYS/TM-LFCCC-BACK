import io
import uuid
from datetime import UTC, datetime

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.exceptions import ConflictError, InsufficientStockError, NotFoundError, UnprocessableError
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductInput, ProductPatchInput
from app.storage.local import LocalStorage

# Pillow re-encode: strips EXIF/payloads and guarantees a real image (magic-bytes alone
# can be spoofed; decoding+saving via Pillow is the practical content check).
_ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
_READ_CHUNK = 64 * 1024


class ProductService:
    def __init__(self, db: Session, storage: LocalStorage | None = None) -> None:
        self._repo = ProductRepository(db)
        self._db = db
        self._storage = storage or LocalStorage()

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        q: str | None = None,
        category: str | None = None,
        is_active: bool | None = True,
        in_stock: bool | None = None,
        sort: str | None = None,
    ) -> tuple[list[Product], int]:
        return self._repo.list_filtered(
            skip=skip,
            limit=limit,
            q=q,
            category=category,
            is_active=is_active,
            in_stock=in_stock,
            sort=sort,
        )

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        items, _ = self.list_filtered(skip=skip, limit=limit, is_active=True)
        return items

    def get_by_id(self, product_id: str) -> Product:
        product = self._repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"Produto com id '{product_id}' não encontrado.")
        return product

    def get_public_by_id(self, product_id: str) -> Product:
        product = self.get_by_id(product_id)
        if not product.is_active:
            raise NotFoundError(f"Produto com id '{product_id}' não encontrado.")
        return product

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, data: ProductInput) -> Product:
        if self._repo.get_by_sku(data.sku) is not None:
            raise ConflictError(f"Já existe um produto com o SKU '{data.sku}'.")
        now = datetime.now(UTC)
        product = Product(
            id=str(uuid.uuid4()),
            sku=data.sku,
            name=data.name,
            description=data.description,
            category=data.category,
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
        return product

    # ── Update (partial) ──────────────────────────────────────────────────────

    def patch(self, product_id: str, data: ProductPatchInput) -> Product:
        product = self.get_by_id(product_id)
        updates = data.model_dump(exclude_unset=True)
        if "sku" in updates and updates["sku"] != product.sku:
            if self._repo.get_by_sku(updates["sku"]) is not None:
                raise ConflictError(f"Já existe um produto com o SKU '{updates['sku']}'.")

        # Cross-field promo vs price when only one side is patched
        new_price = updates.get("price", product.price)
        new_promo = updates.get("promo_price", product.promo_price)
        if "promo_price" in updates or "price" in updates:
            if new_promo is not None and new_promo > new_price:
                raise UnprocessableError("Preço promocional não pode ser maior que o preço")

        for field, value in updates.items():
            setattr(product, field, value)
        self._repo.update(product)
        return product

    # ── Soft delete ───────────────────────────────────────────────────────────

    def soft_delete(self, product_id: str) -> None:
        product = self.get_by_id(product_id)
        if not product.is_active:
            return
        self._repo.soft_delete(product)

    # ── Stock patch ───────────────────────────────────────────────────────────

    def patch_stock(self, product_id: str, delta: int) -> Product:
        product = self.get_by_id(product_id)
        updated = self._repo.update_stock(product_id, delta)
        if updated is None:
            raise InsufficientStockError(
                f"Estoque insuficiente para ajuste. "
                f"Disponível: {product.quantity}, ajuste solicitado: {delta}."
            )
        return updated

    # ── Image upload ──────────────────────────────────────────────────────────

    async def _read_with_limit(self, file: UploadFile) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_IMAGE_BYTES:
                raise UnprocessableError("Arquivo muito grande. Tamanho máximo: 5 MB.")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _reencode_image(raw: bytes) -> tuple[bytes, str]:
        try:
            with Image.open(io.BytesIO(raw)) as img:
                fmt = (img.format or "").upper()
                if fmt not in _ALLOWED_FORMATS:
                    raise UnprocessableError(
                        "Tipo de arquivo não permitido. Use: jpeg, png ou webp."
                    )
                # Normalize mode for JPEG (no alpha). convert() returns Image, not ImageFile.
                working: Image.Image = img
                if fmt == "JPEG" and working.mode in ("RGBA", "P"):
                    working = working.convert("RGB")
                elif working.mode == "P":
                    working = working.convert("RGBA")
                buf = io.BytesIO()
                save_kwargs: dict = {"format": fmt}
                if fmt == "JPEG":
                    save_kwargs["quality"] = 90
                    save_kwargs["optimize"] = True
                working.save(buf, **save_kwargs)
                return buf.getvalue(), _ALLOWED_FORMATS[fmt]
        except UnprocessableError:
            raise
        except UnidentifiedImageError as exc:
            raise UnprocessableError("Arquivo de imagem inválido. Use: jpeg, png ou webp.") from exc
        except OSError as exc:
            raise UnprocessableError("Não foi possível processar a imagem enviada.") from exc

    async def upload_image(self, product_id: str, file: UploadFile) -> Product:
        product = self.get_by_id(product_id)
        raw = await self._read_with_limit(file)
        if not raw:
            raise UnprocessableError("Arquivo vazio.")

        encoded, ext = await run_in_threadpool(self._reencode_image, raw)
        filename = f"{uuid.uuid4()}.{ext}"
        relative = f"products/{filename}"

        old_image = product.image_url
        stored_path = await run_in_threadpool(self._storage.save, relative, encoded)

        product.image_url = stored_path
        self._repo.update(product)

        if old_image and old_image != stored_path:
            await run_in_threadpool(self._storage.delete, old_image)

        return product
