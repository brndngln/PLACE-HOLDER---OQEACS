from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_analyze_repo(async_client: AsyncClient, sample_repo) -> None:
    resp = await async_client.post(
        "/api/v1/analyze",
        json={"repo_path": str(sample_repo), "languages": ["python"], "depth": "full", "include_tests": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_count"] >= 1
    assert body["total_entities"] >= 1


@pytest.mark.anyio
async def test_get_graph(async_client: AsyncClient, sample_repo) -> None:
    created = await async_client.post(
        "/api/v1/analyze",
        json={"repo_path": str(sample_repo), "languages": ["python"], "depth": "full", "include_tests": True},
    )
    repo_id = created.json()["repo_id"]
    resp = await async_client.get(f"/api/v1/graph/{repo_id}")
    assert resp.status_code == 200
    assert resp.json()["repo_id"] == repo_id


@pytest.mark.anyio
async def test_impact_requires_repo_id(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/impact",
        json={"file_path": "main.py", "function_name": "calc", "change_description": "rename"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_dependents_endpoint(async_client: AsyncClient, sample_repo) -> None:
    created = await async_client.post(
        "/api/v1/analyze",
        json={"repo_path": str(sample_repo), "languages": ["python"], "depth": "full", "include_tests": True},
    )
    graph = created.json()
    ent_id = graph["entities"][0]["id"]
    resp = await async_client.get(f"/api/v1/entities/{ent_id}/dependents", params={"repo_id": graph["repo_id"]})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
