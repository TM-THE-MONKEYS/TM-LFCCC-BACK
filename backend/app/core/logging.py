"""Structured logging helpers with correlation_id."""

from __future__ import annotations

import logging

from app.middleware.correlation import correlation_id_ctx

logger = logging.getLogger("vitrine")


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get() or "-"  # type: ignore[attr-defined]
        return True


def configure_logging() -> None:
    """Idempotent basic config for the app logger (safe for create_app)."""
    if any(isinstance(f, CorrelationIdFilter) for f in logger.filters):
        return
    logger.addFilter(CorrelationIdFilter())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s level=%(levelname)s correlation_id=%(correlation_id)s "
                "logger=%(name)s msg=%(message)s"
            )
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
