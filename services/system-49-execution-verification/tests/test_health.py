"""Tests for health and metrics endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_returns_200(async_client: AsyncClient) -> None:
    """GET /health should return 200 with status=healthy."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "omni-exec-verify"
    assert body["version"] == "1.0.0"


@pytest.mark.anyio
async def test_metrics_returns_prometheus_format(async_client: AsyncClient) -> None:
    """GET /metrics should return Prometheus text format."""
    resp = await async_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "") or "openmetrics" in resp.headers.get("content-type", "")
    # Should contain at least one metric family
    assert "http_requests_total" in resp.text or "exec_verify" in resp.text or "python_info" in resp.text
