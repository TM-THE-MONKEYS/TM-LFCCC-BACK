"""Shared ISO / YYYY-MM-DD query-param parsing for list filters."""

from __future__ import annotations

from datetime import UTC, datetime

from app.exceptions import UnprocessableError


def parse_iso_dt(raw: str | None, *, end_of_day: bool = False) -> datetime | None:
    """Parse YYYY-MM-DD or ISO 8601 into timezone-aware UTC datetime."""
    if raw is None or not raw.strip():
        return None
    value = raw.strip()
    try:
        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
            if end_of_day:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999000)
            return dt
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as exc:
        raise UnprocessableError(f"Data inválida: '{raw}'. Use YYYY-MM-DD ou ISO 8601.") from exc
