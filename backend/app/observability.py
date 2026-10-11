"""Structured logs that never contain a CV or a job description.

The privacy rule in the project plan: logs record only a request ID, method and path, status code,
duration, CV size and page count. Every line is one JSON object, so Render's log search can filter
by field. Uvicorn's own access log is switched off in the Dockerfile because it records client IPs.
"""

import contextvars
import json
import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The current request's ID, readable from anywhere that handles the request (and copied into the
# worker threads that do the CPU work).
request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
logger = logging.getLogger("app")


class JsonFormatter(logging.Formatter):
    """Format a log record as one JSON line: time, level, event, request ID and its fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a JSON string."""
        entry = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "request_id": request_id.get(),
            **getattr(record, "fields", {}),
        }
        return json.dumps(entry)


def configure_logging(level: int = logging.INFO) -> None:
    """Send the app's logs to stderr as JSON lines (called once at startup)."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False


def log_event(event: str, **fields: str | int | float) -> None:
    """Log one event with typed fields. Only numbers and short codes belong here, never text."""
    logger.info(event, extra={"fields": fields})


class RequestLog:
    """ASGI middleware: give each request an ID (sent back as X-Request-ID) and log its outcome."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap `app`."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run the request, then log method, path, status and duration."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = uuid.uuid4().hex[:12]
        token = request_id.set(rid)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [*message.get("headers", []), (b"x-request-id", rid.encode())]
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            log_event(
                "request",
                method=scope["method"],
                path=scope["path"],
                status=status,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            request_id.reset(token)
