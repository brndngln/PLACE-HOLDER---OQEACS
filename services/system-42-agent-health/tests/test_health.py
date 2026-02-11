"""
Tests for the /health and /metrics infrastructure endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_healthy(client: TestClient) -> None:
    """GET /health must return 200 with status=healthy."""
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "agent-health"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body
    assert "dependencies" in body
    assert "postgres" in body["dependencies"]
    assert "redis" in body["dependencies"]


def test_health_reports_unavailable_deps(client: TestClient) -> None:
    """When DB/Redis are not connected the health endpoint still returns
    200 but marks dependencies as unavailable."""
    response = client.get("/health")
    body = response.json()
    assert body["dependencies"]["postgres"] == "unavailable"
    assert body["dependencies"]["redis"] == "unavailable"


def test_metrics_returns_prometheus_format(client: TestClient) -> None:
    """GET /metrics must return text/plain Prometheus exposition data."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    text = response.text
    # Should contain our custom metrics
    assert "agent_health_uptime_seconds" in text
    assert "agent_health_requests_total" in text or "agent_health_score" in text


def test_openapi_docs_available(client: TestClient) -> None:
    """The auto-generated OpenAPI JSON must be reachable."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "System 42 \u2014 Agent Health Monitor"
