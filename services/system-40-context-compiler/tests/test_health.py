"""Health and metrics endpoint tests."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "context-compiler"


def test_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "requests_total" in resp.text or "python_info" in resp.text
