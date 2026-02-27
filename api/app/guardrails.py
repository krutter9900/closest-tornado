import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional


@dataclass
class RateLimitConfig:
    max_requests: int = 30
    window_seconds: int = 60


class SimpleRateLimiter:
    """
    In-memory, per-process, per-IP sliding window rate limiter.
    Good for local/dev and single-instance deployments.
    """
    def __init__(self, cfg: RateLimitConfig):
        self.cfg = cfg
        self._hits: Dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.cfg.window_seconds
        q = self._hits.get(key)
        if q is None:
            q = deque()
            self._hits[key] = q

        # drop old hits
        while q and q[0] < window_start:
            q.popleft()

        if len(q) >= self.cfg.max_requests:
            return False

        q.append(now)
        return True


class TTLCache:
    """
    Simple in-memory TTL cache.
    Stores JSON-serializable objects.
    """
    def __init__(self, ttl_seconds: int = 6 * 3600, max_items: int = 5000):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[Tuple[Any, ...], Tuple[float, Any]] = {}

    def get(self, key: Tuple[Any, ...]) -> Optional[Any]:
        now = time.time()
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if now >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: Tuple[Any, ...], value: Any) -> None:
        now = time.time()

        # basic eviction: if too big, drop oldest by expiry time
        if len(self._store) >= self.max_items:
            oldest_key = min(self._store.items(), key=lambda kv: kv[1][0])[0]
            self._store.pop(oldest_key, None)

        self._store[key] = (now + self.ttl, value)