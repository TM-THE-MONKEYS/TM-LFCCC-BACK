"""Gunicorn settings for the production image (values tunable via env, no rebuild).

FORWARDED_ALLOW_IPS must list only the reverse proxy (IP or CIDR, comma-separated).
Never "*": X-Forwarded-For would become client-controlled, which spoofs client_ip
in logs and bypasses the per-IP login rate limit.
"""

import os


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
worker_class = "uvicorn.workers.UvicornWorker"
workers = _int_env("WEB_CONCURRENCY", 2)

timeout = _int_env("GUNICORN_TIMEOUT", 60)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
max_requests = 1000
max_requests_jitter = 100

forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1").strip() or "127.0.0.1"

# Access lines come from RequestLoggingMiddleware (correlation_id, duration, route).
# Leaving gunicorn's access log off avoids one duplicate line per request.
accesslog = None
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
