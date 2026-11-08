"""HTTP request access logging — correlation_id, duration, no secrets/PII values."""

from __future__ import annotations

import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger

_SLOW_MS = 500.0
_VERY_SLOW_MS = 1000.0

# Skip noisy probes / static assets from access logs (still counted by HEALTHCHECK).
_SKIP_PREFIXES = ("/uploads/",)
_SKIP_EXACT = frozenset({"/live", "/health"})


def _slow_tier(duration_ms: float) -> str:
    if duration_ms >= _VERY_SLOW_MS:
        return "very_slow"
    if duration_ms >= _SLOW_MS:
        return "slow"
    return "ok"


def _route_template(request: Request) -> str | None:
    route = request.scope.get("route")
    path_format = getattr(route, "path_format", None) or getattr(route, "path", None)
    return str(path_format) if path_format else None


def _should_skip(path: str) -> bool:
    if path in _SKIP_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _SKIP_PREFIXES)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one structured line per request (keys only for query — never values)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if _should_skip(request.url.path):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        query_keys = sorted({k for k in request.query_params.keys()}) or None
        client_ip = request.client.host if request.client else "unknown"
        route = _route_template(request)
        tier = _slow_tier(duration_ms)

        logger.info(
            "http_request method=%s path=%s route=%s status=%s duration_ms=%s "
            "slow_tier=%s query_keys=%s client_ip=%s",
            request.method,
            request.url.path,
            route or "-",
            response.status_code,
            duration_ms,
            tier,
            query_keys,
            client_ip,
        )
        if tier != "ok":
            logger.warning(
                "slow_request method=%s path=%s status=%s duration_ms=%s slow_tier=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                tier,
            )

        response.headers.setdefault("X-Response-Time-Ms", str(duration_ms))
        return response
