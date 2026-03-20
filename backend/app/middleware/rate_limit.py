"""Simple in-memory rate limiter middleware.

Limits requests per IP address using a sliding window counter.
Designed for auth endpoints; attach via FastAPI dependency injection.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status


class RateLimiter:
    """In-memory sliding-window rate limiter.

    Args:
        max_requests: Maximum number of requests allowed per window.
        window_seconds: Length of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _clean_old_entries(self, key: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_seconds
        self._requests[key] = [
            t for t in self._requests[key] if t > cutoff
        ]

    def is_allowed(self, key: str) -> bool:
        """Check if a request from *key* is allowed and record it."""
        now = time.time()
        with self._lock:
            self._clean_old_entries(key, now)
            if len(self._requests[key]) >= self.max_requests:
                return False
            self._requests[key].append(now)
            return True

    def remaining(self, key: str) -> int:
        """Return how many requests remain in the current window."""
        now = time.time()
        with self._lock:
            self._clean_old_entries(key, now)
            return max(0, self.max_requests - len(self._requests[key]))


# Shared limiter instance for auth endpoints: 100 req/min per IP
auth_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


async def rate_limit_auth(request: Request) -> None:
    """FastAPI dependency that enforces rate limiting on auth endpoints.

    Extracts the client IP from X-Forwarded-For (when behind a proxy) or
    falls back to `request.client.host`.

    Raises:
        HTTPException 429 if the rate limit is exceeded.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    if not auth_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
