"""System 46 — Health and metrics endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_returns_200(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "omni-debate-engine"


@pytest.mark.anyio
async def test_health_includes_version(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.json()["version"] == "1.0.0"


@pytest.mark.anyio
async def test_metrics_returns_prometheus(async_client: AsyncClient) -> None:
    resp = await async_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "http_requests_total" in resp.text


@pytest.mark.anyio
async def test_openapi_schema(async_client: AsyncClient) -> None:
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"].startswith("Omni Quantum")
    assert "/api/v1/debate" in schema["paths"]
    assert "/api/v1/review" in schema["paths"]
