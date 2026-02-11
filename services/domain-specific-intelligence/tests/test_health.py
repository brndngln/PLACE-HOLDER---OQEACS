from fastapi.testclient import TestClient
from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_capability_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/domains")
    assert response.status_code == 200
    assert response.json()["status"] == "enabled"
