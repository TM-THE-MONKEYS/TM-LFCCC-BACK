"""Handlers de exceção HTTP — mapeamento de exceções de domínio para respostas HTTP.

Registre todos os handlers chamando register_exception_handlers(app) no main.py.
"""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorDetail, ErrorResponse
from app.exceptions.domain import (
    AppException,
    ConflictError,
    ForbiddenError,
    InsufficientStockError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableError,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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

    # ── Exceções nativas do FastAPI / Starlette ────────────────────────────────

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(exc.status_code, str(exc.detail))

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
        return error_response(500, "Erro interno do servidor.")
