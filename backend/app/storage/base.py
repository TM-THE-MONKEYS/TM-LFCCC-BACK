from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract storage for product images (local disk today; S3 later)."""

    @abstractmethod
    def save(self, relative_path: str, data: bytes) -> str:
        """Persist bytes at relative_path. Returns the stored relative path."""

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """Delete file if it exists; no-op if missing."""

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Return True if the relative path exists."""
