"""Optional Sentry error reporting — enabled only when SENTRY_DSN is set."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import Settings
from app.core.logging import logger
from app.middleware.correlation import correlation_id_ctx

if TYPE_CHECKING:
    from sentry_sdk._types import Event

# Only unexpected server errors become Sentry events; 4xx are expected client outcomes.
_REPORTED_STATUS_CODES = frozenset(range(500, 600))


def _tag_correlation_id(event: Event, _hint: dict[str, Any]) -> Event | None:
    correlation_id = correlation_id_ctx.get()
    if correlation_id:
        event.setdefault("tags", {})["correlation_id"] = correlation_id
    return event


def init_sentry(cfg: Settings, *, release: str) -> bool:
    """Initialize Sentry if configured. Returns True when enabled."""
    dsn = cfg.SENTRY_DSN.get_secret_value().strip()
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=cfg.ENVIRONMENT,
        release=f"vitrine-backend@{release}",
        send_default_pii=False,
        traces_sample_rate=cfg.SENTRY_TRACES_SAMPLE_RATE,
        before_send=_tag_correlation_id,
        integrations=[
            StarletteIntegration(failed_request_status_codes=set(_REPORTED_STATUS_CODES)),
            FastApiIntegration(failed_request_status_codes=set(_REPORTED_STATUS_CODES)),
        ],
    )
    logger.info("sentry_enabled environment=%s", cfg.ENVIRONMENT)
    return True
