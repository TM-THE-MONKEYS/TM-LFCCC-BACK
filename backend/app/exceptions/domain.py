"""Exceções de domínio — sem acoplamento com HTTP.

Os services lançam estas exceções; os handlers em exceptions/handlers.py
fazem o mapeamento para as respostas HTTP correspondentes.
Assim a lógica de negócio não depende de nada do FastAPI/Starlette.
"""


class AppException(Exception):
    """Base for all application-level domain exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""


class ConflictError(AppException):
    """Raised when an operation would violate a uniqueness constraint."""


class UnauthorizedError(AppException):
    """Raised when authentication is missing or invalid."""


class ForbiddenError(AppException):
    """Raised when the authenticated user lacks permission."""


class UnprocessableError(AppException):
    """Raised when business-rule validation fails (distinct from schema validation)."""


class InsufficientStockError(AppException):
    """Raised when a sale would reduce product stock below zero."""
