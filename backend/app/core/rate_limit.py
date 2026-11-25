"""API Rate Limiter with Redis primary backend and thread-safe in-memory fallback."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.core.config import settings


class RateLimiter:
    """Sliding-window rate limiter supporting Redis and local memory fallback."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory_windows: Dict[str, List[float]] = defaultdict(list)
        self._redis_client: Optional[object] = None
        self._redis_checked = False

    def _get_redis(self):
        if self._redis_checked:
            return self._redis_client
        self._redis_checked = True
        try:
            import redis

            client = redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                decode_responses=True,
            )
            client.ping()
            self._redis_client = client
        except Exception:
            self._redis_client = None
        return self._redis_client

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int]:
        """
        Check whether `key` is within `limit` requests per `window_seconds`.
        Returns `(allowed: bool, remaining: int)`.
        """
        now = time.time()
        redis_client = self._get_redis()
        if redis_client is not None:
            try:
                redis_key = f"fmip:ratelimit:{key}:{int(now // window_seconds)}"
                count = redis_client.incr(redis_key)  # type: ignore[union-attr]
                if count == 1:
                    redis_client.expire(redis_key, window_seconds)  # type: ignore[union-attr]
                allowed = count <= limit
                remaining = max(0, limit - int(count))
                return allowed, remaining
            except Exception:
                pass

        with self._lock:
            cutoff = now - window_seconds
            timestamps = [t for t in self._memory_windows[key] if t > cutoff]
            if len(timestamps) >= limit:
                self._memory_windows[key] = timestamps
                return False, 0
            timestamps.append(now)
            self._memory_windows[key] = timestamps
            return True, max(0, limit - len(timestamps))


rate_limiter = RateLimiter()
