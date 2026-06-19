"""Per-domain token-bucket rate limiting for outbound fetches."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from urllib.parse import urlparse


class DomainRateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.capacity = max(1, per_minute)
        self.refill_rate = self.capacity / 60.0  # tokens per second
        self._tokens: dict[str, float] = defaultdict(lambda: float(self.capacity))
        self._last: dict[str, float] = defaultdict(time.monotonic)
        self._lock = threading.Lock()

    def acquire(self, url: str, *, block: bool = True, timeout: float = 10.0) -> bool:
        host = urlparse(url).hostname or "unknown"
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last[host]
                self._tokens[host] = min(
                    self.capacity, self._tokens[host] + elapsed * self.refill_rate
                )
                self._last[host] = now
                if self._tokens[host] >= 1.0:
                    self._tokens[host] -= 1.0
                    return True
            if not block or time.monotonic() >= deadline:
                return False
            time.sleep(0.05)
