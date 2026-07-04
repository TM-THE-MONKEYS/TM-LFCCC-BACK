"""Middleware de Correlation ID.

Adiciona o header X-Correlation-ID em todas as respostas.
Se o cliente já enviar um, ele é retornado como está; caso contrário, um UUID é gerado.
O correlation ID fica disponível via ContextVar `correlation_id_ctx` para uso
em logs durante o ciclo de vida da requisição.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_HEADER = "X-Correlation-ID"

# ContextVar para que qualquer módulo acesse o correlation ID da requisição atual
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        token = correlation_id_ctx.set(correlation_id)
        try:
            response: Response = await call_next(request)
            response.headers[CORRELATION_HEADER] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)
