"""
System 44 — Health endpoint tests for all four MCP servers.

Verifies that every server responds to GET /health with status 200 and
the expected payload structure.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_analysis_health(analysis_client: AsyncClient) -> None:
    """MCP Analysis server returns healthy status."""
    resp = await analysis_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "mcp-analysis"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body
    assert body["tools_available"] == 4


@pytest.mark.anyio
async def test_test_server_health(test_client: AsyncClient) -> None:
    """MCP Test server returns healthy status."""
    resp = await test_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "mcp-test"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body
    assert body["tools_available"] == 4


@pytest.mark.anyio
async def test_deploy_health(deploy_client: AsyncClient) -> None:
    """MCP Deploy server returns healthy status."""
    resp = await deploy_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "mcp-deploy"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body
    assert body["tools_available"] == 4
    assert "dependencies" in body


@pytest.mark.anyio
async def test_knowledge_health(knowledge_client: AsyncClient) -> None:
    """MCP Knowledge server returns healthy status."""
    resp = await knowledge_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "mcp-knowledge"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body
    assert body["tools_available"] == 4
    assert "dependencies" in body


@pytest.mark.anyio
async def test_analysis_metrics(analysis_client: AsyncClient) -> None:
    """MCP Analysis server exposes Prometheus metrics."""
    resp = await analysis_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "mcp_analysis_uptime_seconds" in text


@pytest.mark.anyio
async def test_test_server_metrics(test_client: AsyncClient) -> None:
    """MCP Test server exposes Prometheus metrics."""
    resp = await test_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "mcp_test_uptime_seconds" in text


@pytest.mark.anyio
async def test_deploy_metrics(deploy_client: AsyncClient) -> None:
    """MCP Deploy server exposes Prometheus metrics."""
    resp = await deploy_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "mcp_deploy_uptime_seconds" in text


@pytest.mark.anyio
async def test_knowledge_metrics(knowledge_client: AsyncClient) -> None:
    """MCP Knowledge server exposes Prometheus metrics."""
    resp = await knowledge_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "mcp_knowledge_uptime_seconds" in text
