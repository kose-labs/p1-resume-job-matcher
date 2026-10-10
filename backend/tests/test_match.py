"""POST /api/v1/match: request validation and upload limits (S7). The matcher is still a stub."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from httpx2 import Response
from starlette.formparsers import MultiPartParser

from app.limits import MAX_CV_BYTES, MAX_REQUEST_BYTES
from app.main import app

client = TestClient(app)

PDF = b"%PDF-1.7\n% synthetic test file, not a real CV\n"
JD = "We are hiring a backend engineer to build and run REST APIs in Python with FastAPI. " * 2


def post(cv: bytes = PDF, job_description: str = JD, filename: str = "cv.pdf") -> Response:
    """Send a multipart match request the way the frontend will."""
    return client.post(
        "/api/v1/match",
        files={"cv": (filename, cv, "application/pdf")},
        data={"job_description": job_description},
    )


def error_code(response: Response) -> str:
    """Return the `code` from one of our own error responses."""
    code: str = response.json()["detail"]["code"]
    return code


def test_valid_request_returns_the_contract_shape() -> None:
    response = post()
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"score", "skills", "evidence", "model", "warnings"}
    assert 0 <= body["score"] <= 1
    assert body["model"]["name"] == "stub"


def test_file_type_is_checked_by_content_not_name() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    response = post(cv=png, filename="cv.pdf")
    assert response.status_code == 415
    assert error_code(response) == "unsupported_file_type"


def test_empty_file_is_rejected() -> None:
    response = post(cv=b"")
    assert response.status_code == 415


def test_cv_over_5_mb_is_rejected() -> None:
    response = post(cv=PDF + b"0" * MAX_CV_BYTES)
    assert response.status_code == 413
    assert error_code(response) == "file_too_large"


def test_oversized_request_is_rejected_from_its_content_length() -> None:
    response = post(cv=PDF + b"0" * MAX_REQUEST_BYTES)
    assert response.status_code == 413
    assert error_code(response) == "file_too_large"


def test_limit_holds_when_content_length_is_missing() -> None:
    boundary = "kose-test-boundary"

    def chunked_body() -> Iterator[bytes]:
        yield (
            f'--{boundary}\r\nContent-Disposition: form-data; name="cv"; filename="cv.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode() + PDF
        for _ in range(MAX_REQUEST_BYTES // 65_536 + 2):
            yield b"0" * 65_536
        yield f"\r\n--{boundary}--\r\n".encode()

    response = client.post(
        "/api/v1/match",
        content=chunked_body(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )
    assert response.status_code == 413
    assert error_code(response) == "file_too_large"


def test_job_description_too_short_is_rejected() -> None:
    assert post(job_description="Python developer").status_code == 422


def test_whitespace_does_not_count_towards_the_minimum() -> None:
    assert post(job_description=" " * 200 + "Python" * 10).status_code == 422


def test_job_description_too_long_is_rejected() -> None:
    assert post(job_description="x" * 20_001).status_code == 422


def test_missing_cv_is_rejected() -> None:
    response = client.post("/api/v1/match", data={"job_description": JD})
    assert response.status_code == 422


def test_uploads_are_kept_in_memory() -> None:
    assert MultiPartParser.spool_max_size >= MAX_REQUEST_BYTES


def test_openapi_documents_the_error_responses() -> None:
    responses = client.get("/openapi.json").json()["paths"]["/api/v1/match"]["post"]["responses"]
    assert {"200", "413", "415", "422"} <= set(responses)
