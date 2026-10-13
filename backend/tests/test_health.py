from fastapi.testclient import TestClient

from app.main import VERSION


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version(client: TestClient) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json() == {"version": VERSION}


def test_root_redirects_to_the_api_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
    assert client.get("/docs").status_code == 200


def test_root_is_not_part_of_the_api_contract(client: TestClient) -> None:
    assert "/" not in client.get("/openapi.json").json()["paths"]
