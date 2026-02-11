"""
System 43 — Health and metrics endpoint tests.

These tests verify that the ``/health`` and ``/metrics`` endpoints
respond correctly without requiring any external dependencies.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(async_client: AsyncClient) -> None:
    """GET /health must return 200 with the expected JSON shape."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "self-testing"
    assert "version" in body


@pytest.mark.asyncio
async def test_health_contains_service_name(async_client: AsyncClient) -> None:
    """The health payload must declare the correct service name."""
    response = await async_client.get("/health")
    assert response.json()["service"] == "self-testing"


@pytest.mark.asyncio
async def test_metrics_returns_prometheus_format(async_client: AsyncClient) -> None:
    """GET /metrics must return a text/plain Prometheus exposition."""
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type or "text/plain" in content_type
    # Prometheus output always contains at least the default process metrics
    assert "python_info" in response.text or "process_" in response.text or "HELP" in response.text


@pytest.mark.asyncio
async def test_openapi_schema_available(async_client: AsyncClient) -> None:
    """The FastAPI OpenAPI schema must be reachable."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]
