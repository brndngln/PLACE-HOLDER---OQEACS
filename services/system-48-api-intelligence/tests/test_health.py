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


@pytest.mark.anyio
async def test_openapi(async_client: AsyncClient) -> None:
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/v1/scan" in resp.json()["paths"]


@pytest.mark.anyio
async def test_compatibility_validation(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/v1/compatibility/matrix", json=[{"name": "fastapi", "version": "0.115.6"}])
    assert resp.status_code == 422
