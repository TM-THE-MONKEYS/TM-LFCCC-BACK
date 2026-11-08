from pathlib import Path

from app.core.config import resolve_upload_dir
from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Filesystem storage under UPLOAD_DIR. Paths stored relative to that root."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir if base_dir is not None else resolve_upload_dir()
        self._base.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base

    def _resolve(self, relative_path: str) -> Path:
        # Strip leading slash / uploads/ prefix so we stay under base
        rel = relative_path.lstrip("/")
        if rel.startswith("uploads/"):
            rel = rel[len("uploads/") :]
        target = (self._base / rel).resolve()
        if not str(target).startswith(str(self._base.resolve())):
            raise ValueError("Caminho de armazenamento inválido.")
        return target

    def save(self, relative_path: str, data: bytes) -> str:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        # Canonical relative path used in DB / public URL builder
        return f"uploads/{relative_path.lstrip('/').removeprefix('uploads/')}"

    def delete(self, relative_path: str) -> None:
        if not relative_path:
            return
        # Ignore absolute/external URLs — nothing local to delete
        if relative_path.startswith("http://") or relative_path.startswith("https://"):
            return
        path = self._resolve(relative_path)
        if path.is_file():
            path.unlink()

    def exists(self, relative_path: str) -> bool:
        if not relative_path or relative_path.startswith(("http://", "https://")):
            return False
        return self._resolve(relative_path).is_file()
