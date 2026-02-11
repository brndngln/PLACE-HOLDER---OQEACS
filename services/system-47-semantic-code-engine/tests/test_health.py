from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_metrics(async_client: AsyncClient) -> None:
    resp = await async_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


@pytest.mark.anyio
async def test_openapi(async_client: AsyncClient) -> None:
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/v1/analyze" in resp.json()["paths"]


@pytest.mark.anyio
async def test_meaning_endpoint(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/v1/meaning", json={"code": "def x():\\n    return 1", "language": "python", "context": ""})
    assert resp.status_code == 200
    assert "summary" in resp.json()
