"""Rate limiting for the match endpoint, applied before the upload is read.

A single in-memory limiter is enough because the API runs as one instance (Render Free). It
resets when the server restarts, which is acceptable for a demo.
"""

import math
import time
from collections import deque
from collections.abc import Callable

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

RATE_LIMITED = "Too many requests. Please wait a minute and try again."


class RateLimiter:
    """Sliding-window limit: at most `limit` requests per key within `window` seconds."""

    def __init__(
        self, limit: int, window: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Create a limiter; `clock` is injectable so tests don't have to wait."""
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> float | None:
        """Record a request for `key`. Return seconds to wait if it's over the limit, else None.

        Rejected requests are not recorded, so a client that keeps retrying isn't locked out longer.
        """
        now = self.clock()
        if len(self._hits) > 10_000:
            self._forget_idle(now)
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            # With limit=0 there are no recorded hits; the client waits a full window.
            return hits[0] + self.window - now if hits else self.window
        hits.append(now)
        return None

    def reset(self) -> None:
        """Forget every recorded request."""
        self._hits.clear()

    def _forget_idle(self, now: float) -> None:
        """Drop keys with no requests inside the window, so memory doesn't grow without bound."""
        idle = [
            key for key, hits in self._hits.items() if not hits or hits[-1] <= now - self.window
        ]
        for key in idle:
            del self._hits[key]


class RateLimit:
    """ASGI middleware that applies `limiter` per client IP to one method and path."""

    def __init__(self, app: ASGIApp, limiter: RateLimiter, method: str, path: str) -> None:
        """Wrap `app`, limiting only requests to `method` `path`."""
        self.app = app
        self.limiter = limiter
        self.method = method
        self.path = path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject the request with 429 and `Retry-After` if its client is over the limit."""
        if (
            scope["type"] == "http"
            and scope["method"] == self.method
            and scope["path"] == self.path
        ):
            client = scope.get("client")
            wait = self.limiter.check(client[0] if client else "unknown")
            if wait is not None:
                response = JSONResponse(
                    {"detail": {"code": "rate_limited", "message": RATE_LIMITED}},
                    status_code=429,
                    headers={"Retry-After": str(math.ceil(wait))},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# 10 per minute per client, as in the API contract.
match_limiter = RateLimiter(limit=10, window=60)
