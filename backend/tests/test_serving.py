"""Serving (S9, ADR-0005): the model loads once at startup, and slow matches don't block /health."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.matching import get_match_service
from app.schemas import MatchResponse
from tests.fakes import StubMatchService
from tests.pdfs import TEXT_PDF

JD = "We are hiring a backend engineer to build and run REST APIs in Python with FastAPI. " * 2


def post_match(client: TestClient) -> int:
    files = {"cv": ("cv.pdf", TEXT_PDF, "application/pdf")}
    return client.post("/api/v1/match", files=files, data={"job_description": JD}).status_code


def test_startup_loads_the_service_and_the_cpu_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def loader() -> StubMatchService:
        calls.append("load")
        return StubMatchService()

    monkeypatch.setattr(main, "load_match_service", loader)
    fresh = FastAPI()

    async def start_and_stop() -> None:
        async with main.lifespan(fresh):
            assert isinstance(fresh.state.match_service, StubMatchService)
            assert fresh.state.cpu_limiter.total_tokens == main.MATCH_CONCURRENCY

    asyncio.run(start_and_stop())
    assert calls == ["load"]


def test_requests_reuse_the_loaded_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def must_not_load() -> StubMatchService:
        raise AssertionError("the model must load at startup, not per request")

    monkeypatch.setattr(main, "load_match_service", must_not_load)
    assert [post_match(client) for _ in range(3)] == [200, 200, 200]


class SlowService:
    """Stands in for a CPU-heavy model: each match takes a while, and we record how many overlap."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.active = 0
        self.most_at_once = 0
        self.lock = threading.Lock()

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        with self.lock:
            self.active += 1
            self.most_at_once = max(self.most_at_once, self.active)
        time.sleep(self.seconds)  # blocks a worker thread, like real model work
        with self.lock:
            self.active -= 1
        return StubMatchService().match(cv_text, job_description)


def test_health_stays_fast_and_matches_are_capped_while_slow_matches_run(
    client: TestClient,
) -> None:
    slow = SlowService(seconds=0.4)
    # Override on the app this client serves: test_cors reloads app.main, so `main.app` may be a
    # different object by now.
    served = cast(FastAPI, client.app)
    served.dependency_overrides[get_match_service] = lambda: slow
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            matches = [pool.submit(post_match, client) for _ in range(4)]
            time.sleep(0.15)  # let the matches start
            started = time.perf_counter()
            health = client.get("/health")
            health_seconds = time.perf_counter() - started
            statuses = [m.result() for m in matches]
    finally:
        served.dependency_overrides.clear()

    assert health.status_code == 200
    # If matching ran on the event loop, /health would wait for a 0.4 s match.
    assert health_seconds < 0.25
    assert statuses == [200] * 4
    # The CPU limit holds: never more than MATCH_CONCURRENCY matches at once.
    assert slow.most_at_once == main.MATCH_CONCURRENCY
