"""Unit tests for shared ISO date query parsing."""

from datetime import UTC

import pytest

from app.api.datetime_parse import parse_iso_dt
from app.exceptions import UnprocessableError


def test_parse_none_returns_none():
    assert parse_iso_dt(None) is None
    assert parse_iso_dt("  ") is None


def test_parse_date_only():
    dt = parse_iso_dt("2026-11-08")
    assert dt is not None
    assert dt.tzinfo == UTC
    assert dt.hour == 0


def test_parse_date_only_end_of_day():
    dt = parse_iso_dt("2026-11-08", end_of_day=True)
    assert dt is not None
    assert dt.hour == 23
    assert dt.minute == 59


def test_parse_iso_with_z():
    dt = parse_iso_dt("2026-11-08T12:30:00Z")
    assert dt is not None
    assert dt.hour == 12
    assert dt.minute == 30


def test_parse_invalid_raises():
    with pytest.raises(UnprocessableError):
        parse_iso_dt("not-a-date")
