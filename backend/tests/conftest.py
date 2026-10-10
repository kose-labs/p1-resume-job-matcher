"""Shared test setup."""

from collections.abc import Iterator

import pytest

from app.ratelimit import match_limiter


@pytest.fixture(autouse=True)
def fresh_rate_limit() -> Iterator[None]:
    """Give every test its own rate-limit budget, so tests don't trip each other's limits."""
    match_limiter.reset()
    yield
    match_limiter.reset()
