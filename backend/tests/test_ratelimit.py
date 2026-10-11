"""Rate limiting: 10 match requests per minute per client, rejected before the upload is read."""

import asyncio

from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.main import app
from app.ratelimit import RateLimit, RateLimiter, client_ip

client = TestClient(app)

PDF = b"%PDF-1.7\n% synthetic test file\n"
JD = "We are hiring a backend engineer to build and run REST APIs in Python with FastAPI. " * 2


class FakeClock:
    """A clock the test moves forward by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_allows_up_to_the_limit_then_says_how_long_to_wait() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=3, window=60, clock=clock)
    assert [limiter.check("a") for _ in range(3)] == [None, None, None]
    clock.now += 15
    assert limiter.check("a") == 45  # the oldest request leaves the window in 45 s


def test_limiter_window_slides() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window=60, clock=clock)
    assert limiter.check("a") is None
    clock.now += 60
    assert limiter.check("a") is None


def test_clients_have_separate_budgets() -> None:
    limiter = RateLimiter(limit=1, window=60, clock=FakeClock())
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert limiter.check("a") is not None


def test_idle_clients_are_forgotten() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window=60, clock=clock)
    for i in range(10_001):
        limiter.check(f"client-{i}")
    clock.now += 61
    limiter.check("new-client")
    assert len(limiter._hits) == 1


def test_eleventh_match_request_in_a_minute_gets_429() -> None:
    def post() -> int:
        files = {"cv": ("cv.pdf", PDF, "application/pdf")}
        return client.post("/api/v1/match", files=files, data={"job_description": JD}).status_code

    assert [post() for _ in range(10)] == [200] * 10
    response = client.post(
        "/api/v1/match",
        files={"cv": ("cv.pdf", PDF, "application/pdf")},
        data={"job_description": JD},
    )
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "rate_limited"
    assert 1 <= int(response.headers["retry-after"]) <= 60


def test_other_endpoints_are_not_limited() -> None:
    assert all(client.get("/health").status_code == 200 for _ in range(15))


def test_rejected_before_the_body_is_read() -> None:
    calls: list[str] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        calls.append("app")

    async def receive() -> Message:
        calls.append("body read")
        return {"type": "http.request", "body": b""}

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    limiter = RateLimiter(limit=0, window=60)
    middleware = RateLimit(inner, limiter, method="POST", path="/api/v1/match")
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/match",
        "headers": [],
        "client": ("203.0.113.7", 50000),
    }
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["status"] == 429
    assert "app" not in calls
    assert "body read" not in calls


def test_request_without_client_address_is_still_limited() -> None:
    sent: list[Message] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        raise AssertionError("should not be reached")

    async def receive() -> Message:
        return {"type": "http.request", "body": b""}

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = RateLimit(inner, RateLimiter(limit=0, window=60), "POST", "/api/v1/match")
    scope: Scope = {"type": "http", "method": "POST", "path": "/api/v1/match", "headers": []}
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["status"] == 429


# --- Which address is the client? (behind trusted proxies that append to X-Forwarded-For)

PEER = "10.1.2.3"  # the last proxy, as the app's socket sees it


def scope_with(*forwarded_for: str) -> Scope:
    """An HTTP scope from PEER with the given X-Forwarded-For headers."""
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded_for]
    return {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/match",
        "headers": headers,
        "client": (PEER, 443),
    }


def test_without_trusted_proxies_the_header_is_ignored() -> None:
    assert client_ip(scope_with("203.0.113.7"), trusted_hops=0) == PEER


def test_client_is_the_entry_as_many_places_from_the_right_as_there_are_proxies() -> None:
    # The client forged 6.6.6.6; the edge proxy appended the real 203.0.113.7, the next proxy
    # appended the edge's address.
    scope = scope_with("6.6.6.6, 203.0.113.7, 172.16.0.2")
    assert client_ip(scope, trusted_hops=2) == "203.0.113.7"


def test_repeated_headers_are_read_as_one_list() -> None:
    scope = scope_with("6.6.6.6", "203.0.113.7")
    assert client_ip(scope, trusted_hops=1) == "203.0.113.7"


def test_too_few_entries_falls_back_to_the_peer() -> None:
    assert client_ip(scope_with("203.0.113.7"), trusted_hops=2) == PEER
    assert client_ip(scope_with(), trusted_hops=1) == PEER


def run_limited(middleware: RateLimit, scope: Scope) -> int:
    """Send one request through the middleware and return the status it answered with."""
    statuses: list[int] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b""}

    async def send(message: Message) -> None:
        if message["type"] == "http.response.start":
            statuses.append(message["status"])

    asyncio.run(middleware(scope, receive, send))
    return statuses[0]


async def ok_app(scope: Scope, receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def test_forged_addresses_share_the_real_clients_budget() -> None:
    middleware = RateLimit(
        ok_app, RateLimiter(limit=2, window=60), "POST", "/api/v1/match", trusted_hops=1
    )
    statuses = [run_limited(middleware, scope_with(f"10.0.0.{i}, 203.0.113.7")) for i in range(3)]
    assert statuses == [200, 200, 429]


def test_different_real_clients_get_separate_budgets() -> None:
    middleware = RateLimit(
        ok_app, RateLimiter(limit=1, window=60), "POST", "/api/v1/match", trusted_hops=1
    )
    assert run_limited(middleware, scope_with("203.0.113.7")) == 200
    assert run_limited(middleware, scope_with("198.51.100.4")) == 200
