"""Optional Sentry: off without DSN; when on, no PII and only 5xx reported."""

from __future__ import annotations

from typing import Any

import pytest
import sentry_sdk

from app.core.config import Settings
from app.core.observability import _tag_correlation_id, init_sentry
from app.middleware.correlation import correlation_id_ctx

_FAKE_DSN = "https://publickey@o0.ingest.sentry.io/0"


@pytest.fixture
def captured_init(monkeypatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def _fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", _fake_init)
    return captured


def test_sentry_disabled_without_dsn(monkeypatch, captured_init):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry(Settings(_env_file=None), release="1.0.0") is False
    assert captured_init == {}


def test_sentry_enabled_with_dsn_and_safe_defaults(monkeypatch, captured_init):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_DSN", _FAKE_DSN)

    assert init_sentry(Settings(_env_file=None), release="1.2.3") is True

    assert captured_init["dsn"] == _FAKE_DSN
    assert captured_init["send_default_pii"] is False
    assert captured_init["environment"] == "test"
    assert captured_init["release"] == "vitrine-backend@1.2.3"
    assert captured_init["traces_sample_rate"] == 0.0
    for integration in captured_init["integrations"]:
        codes = integration.failed_request_status_codes
        assert 500 in codes and 503 in codes
        assert not {400, 401, 403, 404, 409, 422, 429} & set(codes)


def test_sentry_dsn_is_not_exposed_in_settings_repr(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", _FAKE_DSN)
    assert "publickey" not in repr(Settings(_env_file=None))


def test_sentry_event_tagged_with_correlation_id():
    token = correlation_id_ctx.set("req-123")
    try:
        event = _tag_correlation_id({"message": "boom"}, {})
    finally:
        correlation_id_ctx.reset(token)
    assert event["tags"]["correlation_id"] == "req-123"


def test_sentry_event_without_correlation_id_untouched():
    event = _tag_correlation_id({"message": "boom"}, {})
    assert "tags" not in event
