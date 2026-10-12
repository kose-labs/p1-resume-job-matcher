"""Privacy rule from the project plan: logs never contain the CV or the job description."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from app.limits import MAX_REQUEST_BYTES
from app.observability import JsonFormatter, logger
from tests.pdfs import CV_LINES, image_only_pdf, text_pdf

# Made-up words that can only reach a log line if CV or job description text leaked into it.
CV_MARKER = "Zanzibar-quokka-7f3a"
JD_MARKER = "Kilimanjaro-okapi-91c2"
CV_PDF = text_pdf(lines=[*CV_LINES, f"Led the {CV_MARKER} migration to PostgreSQL."])
JD = f"We are hiring a backend engineer for {JD_MARKER} to build REST APIs with FastAPI. " * 2

# Every field a log line may carry: numbers, codes and names, never free text.
ALLOWED_FIELDS = {
    "time", "level", "event", "request_id",
    "method", "path", "status", "duration_ms",
    "outcome", "cv_bytes", "pages", "model",
}  # fmt: skip


class Capture(logging.Handler):
    """Collect formatted log lines."""

    def __init__(self, level: int, lines: list[str]) -> None:
        super().__init__(level)
        self.setFormatter(JsonFormatter())
        self.lines = lines

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


@contextmanager
def captured() -> Iterator[list[str]]:
    """Collect what production would log: the app's lines, and warnings from any library."""
    lines: list[str] = []
    app_handler, any_handler = Capture(logging.INFO, lines), Capture(logging.WARNING, lines)
    logger.addHandler(app_handler)
    logging.getLogger().addHandler(any_handler)
    try:
        yield lines
    finally:
        logger.removeHandler(app_handler)
        logging.getLogger().removeHandler(any_handler)


def events(lines: list[str], name: str) -> list[dict[str, object]]:
    entries = [json.loads(line) for line in lines]
    return [entry for entry in entries if entry.get("event") == name]


def post(client: TestClient, cv: bytes) -> int:
    files = {"cv": ("cv.pdf", cv, "application/pdf")}
    return client.post("/api/v1/match", files=files, data={"job_description": JD}).status_code


def test_a_match_is_logged_without_any_cv_or_job_text(client: TestClient) -> None:
    with captured() as lines:
        files = {"cv": ("cv.pdf", CV_PDF, "application/pdf")}
        response = client.post("/api/v1/match", files=files, data={"job_description": JD})

    assert response.status_code == 200
    everything = "\n".join(lines)
    assert CV_MARKER not in everything
    assert JD_MARKER not in everything

    [match] = events(lines, "match")
    assert match["outcome"] == "ok"
    assert match["cv_bytes"] == len(CV_PDF)
    assert match["pages"] == 1
    [request] = events(lines, "request")
    assert request["status"] == 200
    assert request["path"] == "/api/v1/match"
    assert request["request_id"] == response.headers["x-request-id"] == match["request_id"]


def test_a_rejected_pdf_logs_only_the_error_code(client: TestClient) -> None:
    with captured() as lines:
        assert post(client, image_only_pdf()) == 422
    [match] = events(lines, "match")
    assert match["outcome"] == "pdf_no_text"
    assert JD_MARKER not in "\n".join(lines)


def test_answers_from_the_limit_middleware_are_logged_too(client: TestClient) -> None:
    with captured() as lines:
        response = client.post(
            "/api/v1/match",
            headers={"Content-Length": str(MAX_REQUEST_BYTES + 1)},
            content=b"",
        )
    assert response.status_code == 413
    [request] = events(lines, "request")
    assert request["status"] == 413


def test_log_lines_only_carry_known_fields(client: TestClient) -> None:
    with captured() as lines:
        assert post(client, CV_PDF) == 200
        assert post(client, image_only_pdf()) == 422
    assert len(lines) == 4  # a request and a match line for each
    for line in lines:
        assert set(json.loads(line)) <= ALLOWED_FIELDS, line


def test_uvicorn_access_log_is_off_in_the_image() -> None:
    # Uvicorn's access log would record every visitor's IP address.
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text(encoding="utf-8")
    assert "--no-access-log" in dockerfile
