"""
System 44 — Shared test fixtures.

Provides HTTPX AsyncClient fixtures for all four MCP server applications,
allowing tests to call endpoints without a live server.
"""

from __future__ import annotations

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.mcp_servers.analysis import app as analysis_app
from src.mcp_servers.deploy import app as deploy_app
from src.mcp_servers.knowledge import app as knowledge_app
from src.mcp_servers.test_server import app as test_app


@pytest.fixture
async def analysis_client() -> AsyncIterator[AsyncClient]:
    """Async test client for the MCP Analysis server."""
    transport = ASGITransport(app=analysis_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_client() -> AsyncIterator[AsyncClient]:
    """Async test client for the MCP Test server."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def deploy_client() -> AsyncIterator[AsyncClient]:
    """Async test client for the MCP Deploy server."""
    transport = ASGITransport(app=deploy_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def knowledge_client() -> AsyncIterator[AsyncClient]:
    """Async test client for the MCP Knowledge server."""
    transport = ASGITransport(app=knowledge_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
