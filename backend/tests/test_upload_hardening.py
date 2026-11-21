"""Upload hardening: pixel ceiling, file cleanup tied to commit, storage path traversal."""

from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import anyio
import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.services.product_service import ProductService
from app.storage.local import LocalStorage
from tests.conftest import MIN_PNG, upload_image


def _png_header_only(width: int, height: int) -> bytes:
    """PNG whose IHDR claims width×height but carries no real pixel data."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b""))
        + chunk(b"IEND", b"")
    )


# ── Pixel ceiling ────────────────────────────────────────────────────────────


def test_upload_above_pixel_limit_returns_422_without_decoding(
    client, created_product, admin_headers, tmp_storage
):
    # 8000×6250 = 50 MP > default 40 MP; the file is a few bytes (header only).
    r = upload_image(client, created_product["id"], _png_header_only(8000, 6250), admin_headers)

    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert "resolução" in body["message"].lower()
    assert not list(tmp_storage.base_dir.rglob("*.png"))


def test_upload_decompression_bomb_returns_422(client, created_product, admin_headers, tmp_storage):
    r = upload_image(client, created_product["id"], _png_header_only(20000, 20000), admin_headers)

    assert r.status_code == 422
    assert "resolução" in r.json()["message"].lower()


def test_pixel_limit_is_configurable(
    client, created_product, admin_headers, tmp_storage, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "MAX_IMAGE_PIXELS", 1)
    tiny_but_two_pixels = _png_header_only(2, 1)

    r = upload_image(client, created_product["id"], tiny_but_two_pixels, admin_headers)

    assert r.status_code == 422


def test_upload_within_pixel_limit_succeeds(client, created_product, admin_headers, tmp_storage):
    assert upload_image(client, created_product["id"], MIN_PNG, admin_headers).status_code == 200


# ── Old image removed only after commit ──────────────────────────────────────


def _service_upload(service: ProductService, product_id: str) -> str:
    async def _run() -> str:
        file = UploadFile(file=io.BytesIO(MIN_PNG), filename="img.png")
        product = await service.upload_image(product_id, file)
        assert product.image_url is not None
        return product.image_url

    return anyio.run(_run)


def _file_for(storage: LocalStorage, stored: str) -> Path:
    return storage.base_dir / stored.removeprefix("uploads/")


def test_old_image_kept_until_commit_then_deleted(db: Session, created_product, tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    service = ProductService(db, storage=storage)
    first = _service_upload(service, created_product["id"])
    db.commit()

    second = _service_upload(service, created_product["id"])
    assert _file_for(storage, first).is_file(), "old image must survive until commit"

    db.commit()
    assert not _file_for(storage, first).exists()
    assert _file_for(storage, second).is_file()


def test_rollback_keeps_old_image_and_discards_new(db: Session, created_product, tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    service = ProductService(db, storage=storage)
    first = _service_upload(service, created_product["id"])
    db.commit()

    second = _service_upload(service, created_product["id"])
    db.rollback()

    assert _file_for(storage, first).is_file()
    assert not _file_for(storage, second).exists()


def test_after_commit_callback_failure_is_logged_not_raised(db: Session, caplog):
    from app.core.database import on_commit

    def _boom() -> None:
        raise OSError("disk gone")

    on_commit(db, _boom)
    db.commit()

    assert any("db_commit_callback_failed" in rec.getMessage() for rec in caplog.records)


# ── Storage path traversal ───────────────────────────────────────────────────


def test_storage_rejects_parent_traversal(tmp_path: Path):
    storage = LocalStorage(base_dir=tmp_path / "uploads")
    with pytest.raises(ValueError):
        storage.save("../escape.png", b"x")


def test_storage_rejects_sibling_dir_with_same_prefix(tmp_path: Path):
    """String-prefix checks accept /x/uploads-evil for base /x/uploads; is_relative_to does not."""
    storage = LocalStorage(base_dir=tmp_path / "uploads")
    with pytest.raises(ValueError):
        storage.save("../uploads-evil/a.png", b"x")
    assert not (tmp_path / "uploads-evil").exists()


def test_storage_accepts_nested_relative_path(tmp_path: Path):
    storage = LocalStorage(base_dir=tmp_path)
    stored = storage.save("products/ok.png", b"x")
    assert stored == "uploads/products/ok.png"
    assert storage.exists(stored)
