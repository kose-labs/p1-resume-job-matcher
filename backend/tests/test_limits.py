"""BodySizeLimit paths that requests through TestClient don't reach."""

import asyncio

from starlette.types import Message, Receive, Scope, Send

from app.limits import BodySizeLimit


async def ignore(message: Message) -> None:
    """Stand-in for `send` when the test doesn't look at responses."""


def test_non_http_traffic_passes_through_untouched() -> None:
    seen: list[str] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    asyncio.run(BodySizeLimit(inner, max_bytes=10)({"type": "lifespan"}, receive, ignore))
    assert seen == ["lifespan"]


def test_disconnect_messages_are_passed_on_without_counting() -> None:
    received: list[Message] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        received.append(await receive())

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    scope: Scope = {"type": "http", "headers": []}
    asyncio.run(BodySizeLimit(inner, max_bytes=0)(scope, receive, ignore))
    assert received == [{"type": "http.disconnect"}]
