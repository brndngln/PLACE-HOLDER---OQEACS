import asyncio

import httpx
from app.main import app


def test_health() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200

    asyncio.run(_run())


def test_sampling_update() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            updated = await client.put("/api/v1/pipelines/sampling", json={"ratio": 0.4})
        assert updated.status_code == 200
        assert updated.json()["ratio"] == 0.4

    asyncio.run(_run())


def test_instrumentation_check_validation() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            bad = await client.post(
                "/api/v1/instrumentation/check",
                json={"service_url": "x", "endpoint": "/health", "method": "GET"},
            )
        assert bad.status_code == 422

    asyncio.run(_run())
