"""Handlers de exceção HTTP — mapeamento de exceções de domínio para respostas HTTP.

Registre todos os handlers chamando register_exception_handlers(app) no create_app.
"""

from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger
from app.exceptions.domain import (
    ConflictError,
    ForbiddenError,
    InsufficientStockError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableError,
)
from app.schemas.common import ErrorDetail, ErrorResponse


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def error_response(
    status: int,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        status=status,
        message=message,
        details=details,
        timestamp=_now_iso(),
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    # ── Domain exceptions → HTTP ──────────────────────────────────────────────

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return error_response(404, exc.message)

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return error_response(409, exc.message)

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return error_response(401, exc.message)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return error_response(403, exc.message)

    @app.exception_handler(UnprocessableError)
    async def unprocessable_handler(request: Request, exc: UnprocessableError) -> JSONResponse:
        return error_response(422, exc.message)

    @app.exception_handler(InsufficientStockError)
    async def insufficient_stock_handler(
        request: Request, exc: InsufficientStockError
    ) -> JSONResponse:
        return error_response(409, exc.message)

    # ── SQLAlchemy constraint / data errors ───────────────────────────────────

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("integrity_error path=%s", request.url.path)
        return error_response(409, "Conflito de integridade nos dados.")

    @app.exception_handler(DataError)
    async def data_error_handler(request: Request, exc: DataError) -> JSONResponse:
        logger.warning("data_error path=%s", request.url.path)
        return error_response(422, "Dados inválidos para persistência.")

    # ── Starlette/FastAPI HTTP (inclui 404 de rota desconhecida) ──────────────

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else str(detail)
        return error_response(exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[ErrorDetail] = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            details.append(ErrorDetail(field=field, message=error["msg"]))
        return error_response(422, "Erro de validação dos dados enviados.", details)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception path=%s method=%s",
            request.url.path,
            request.method,
        )
        return error_response(500, "Erro interno do servidor.")
