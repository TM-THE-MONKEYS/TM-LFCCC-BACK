"""Pure ASGI Correlation ID middleware.

Adds X-Correlation-ID on every response. Client-supplied values are accepted only
when they match length/charset rules; otherwise a UUID is generated.
Available via ContextVar `correlation_id_ctx` for structured logging.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

CORRELATION_HEADER = "X-Correlation-ID"
_MAX_LEN = 128
_VALID_RE = re.compile(r"^[A-Za-z0-9._\-]+$")

# ContextVar para que qualquer módulo acesse o correlation ID da requisição atual
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def _normalize_correlation_id(raw: str | None) -> str:
    if raw is None:
        return str(uuid.uuid4())
    value = raw.strip()
    if not value or len(value) > _MAX_LEN or not _VALID_RE.fullmatch(value):
        return str(uuid.uuid4())
    return value


class CorrelationIdMiddleware:
    """Pure ASGI middleware (no BaseHTTPMiddleware)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        correlation_id = _normalize_correlation_id(headers.get(CORRELATION_HEADER.lower()))
        token = correlation_id_ctx.set(correlation_id)

        async def send_with_correlation(message) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers") or [])
                header_name = CORRELATION_HEADER.lower().encode("latin-1")
                raw_headers = [(k, v) for k, v in raw_headers if k.lower() != header_name]
                raw_headers.append(
                    (CORRELATION_HEADER.encode("latin-1"), correlation_id.encode("latin-1"))
                )
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        finally:
            correlation_id_ctx.reset(token)
