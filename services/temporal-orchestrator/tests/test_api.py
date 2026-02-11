import asyncio

import httpx
from app.main import app


def test_health() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    asyncio.run(_run())


def test_definition_and_run_lifecycle() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_def = await client.post(
                "/api/v1/workflows/definitions",
                json={
                    "name": "build-release",
                    "task_queue": "omni-build",
                    "workflow_type": "BuildWorkflow",
                    "input_schema": {"artifact": "string"},
                },
            )
            assert create_def.status_code == 200
            definition_id = create_def.json()["id"]

            run = await client.post(
                "/api/v1/workflows/runs",
                json={"definition_id": definition_id, "input_payload": {"artifact": "api"}, "timeout_seconds": 30},
            )
            assert run.status_code == 200
            run_id = run.json()["id"]

            fetched = await client.get(f"/api/v1/workflows/runs/{run_id}")
            assert fetched.status_code == 200
            assert fetched.json()["definition_id"] == definition_id

    asyncio.run(_run())


def test_missing_definition_rejected() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/workflows/runs",
                json={"definition_id": "wfd-missing", "input_payload": {}, "timeout_seconds": 30},
            )
        assert response.status_code == 404

    asyncio.run(_run())
