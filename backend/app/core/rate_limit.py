"""Simple in-memory sliding-window rate limiter (stdlib only).

Intended for login protection. Not shared across workers — fine for a single
process / small deployment; use a Redis-backed limiter if you scale horizontally.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: float = 60.0) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_attempts:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


# Login: 10 attempts / minute per IP+email
login_rate_limiter = InMemoryRateLimiter(max_attempts=10, window_seconds=60.0)
