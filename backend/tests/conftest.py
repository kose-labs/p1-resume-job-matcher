"""Shared test setup."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ratelimit import match_limiter


@pytest.fixture(autouse=True)
def fresh_rate_limit() -> Iterator[None]:
    """Give every test its own rate-limit budget, so tests don't trip each other's limits."""
    match_limiter.reset()
    yield
    match_limiter.reset()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """One test client for the whole run. Entering it runs the app's startup (lifespan), which
    loads the match service, exactly as the server does before accepting requests."""
    with TestClient(app) as test_client:
        yield test_client
