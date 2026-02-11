"""Tests for /health and /metrics endpoints.

System 45 - Knowledge Freshness Service.
"""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient) -> None:
        """Health response should contain required fields."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "checks" in data

    def test_health_service_name(self, client: TestClient) -> None:
        """Health response should report the correct service name."""
        response = client.get("/health")
        data = response.json()
        assert data["service"] == "knowledge-freshness"

    def test_health_version(self, client: TestClient) -> None:
        """Health response should report version 1.0.0."""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "1.0.0"

    def test_health_checks_present(self, client: TestClient) -> None:
        """Health checks dict should contain subsystem statuses."""
        response = client.get("/health")
        data = response.json()
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "qdrant" in checks
        assert "scheduler" in checks

    def test_health_not_configured_deps(self, client: TestClient) -> None:
        """When deps are None, checks should report not_configured."""
        response = client.get("/health")
        data = response.json()
        checks = data["checks"]
        assert checks["database"] == "not_configured"
        assert checks["redis"] == "not_configured"
        assert checks["qdrant"] == "not_configured"


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    def test_metrics_returns_200(self, client: TestClient) -> None:
        """Metrics endpoint should return HTTP 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client: TestClient) -> None:
        """Metrics should be served as Prometheus text format."""
        response = client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type

    def test_metrics_contains_counters(self, client: TestClient) -> None:
        """Metrics output should include defined counters and histograms."""
        response = client.get("/metrics")
        text = response.text
        assert "http_requests_total" in text or "http_request_duration_seconds" in text
