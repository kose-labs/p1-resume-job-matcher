"""CORS stays off unless CORS_ORIGINS lists the frontend origins allowed to call the API."""

import importlib
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main

ALLOWED = "https://frontend.example"


@pytest.fixture
def cors_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    # main builds the app when it is imported, so reload it with the variable set,
    # then reload it again afterwards so other tests get the default app back.
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED)
    application: FastAPI = importlib.reload(main).app
    yield application
    monkeypatch.delenv("CORS_ORIGINS")
    importlib.reload(main)


def test_cors_off_by_default() -> None:
    response = TestClient(main.app).get("/health", headers={"Origin": ALLOWED})
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_configured_origin(cors_app: FastAPI) -> None:
    response = TestClient(cors_app).get("/health", headers={"Origin": ALLOWED})
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_cors_rejects_other_origins(cors_app: FastAPI) -> None:
    response = TestClient(cors_app).get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
