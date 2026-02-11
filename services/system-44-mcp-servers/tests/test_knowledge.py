"""
System 44 — MCP Knowledge Server tool tests.

Validates the tool listing endpoint and verifies that tool definitions
have the expected structure and content.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_knowledge_tools(knowledge_client: AsyncClient) -> None:
    """GET /api/v1/tools returns all four knowledge tools."""
    resp = await knowledge_client.get("/api/v1/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    assert len(tools) == 4

    names = {t["name"] for t in tools}
    assert names == {
        "search_knowledge",
        "get_architecture_decisions",
        "find_similar_code",
        "get_best_practices",
    }


@pytest.mark.anyio
async def test_knowledge_tool_definitions_have_schemas(knowledge_client: AsyncClient) -> None:
    """Every knowledge tool has complete schemas and descriptions."""
    resp = await knowledge_client.get("/api/v1/tools")
    tools = resp.json()
    for tool in tools:
        assert tool["name"], "Tool is missing name"
        assert tool["description"], f"{tool['name']} has empty description"
        assert "input_schema" in tool, f"{tool['name']} missing input_schema"
        assert "output_schema" in tool, f"{tool['name']} missing output_schema"
        assert tool["input_schema"].get("type") == "object", (
            f"{tool['name']} input_schema is not an object type"
        )
        assert "properties" in tool["input_schema"], (
            f"{tool['name']} input_schema missing properties"
        )
        assert "properties" in tool["output_schema"], (
            f"{tool['name']} output_schema missing properties"
        )


@pytest.mark.anyio
async def test_search_knowledge_tool_schema(knowledge_client: AsyncClient) -> None:
    """search_knowledge has the expected input properties."""
    resp = await knowledge_client.get("/api/v1/tools")
    tools = resp.json()
    search_tool = next(t for t in tools if t["name"] == "search_knowledge")
    props = search_tool["input_schema"]["properties"]
    assert "query" in props
    assert "collections" in props
    assert "limit" in props
    assert search_tool["input_schema"]["required"] == ["query"]


@pytest.mark.anyio
async def test_get_architecture_decisions_schema(knowledge_client: AsyncClient) -> None:
    """get_architecture_decisions accepts query, status, and limit."""
    resp = await knowledge_client.get("/api/v1/tools")
    tools = resp.json()
    adr_tool = next(t for t in tools if t["name"] == "get_architecture_decisions")
    props = adr_tool["input_schema"]["properties"]
    assert "query" in props
    assert "status" in props
    assert "limit" in props
    # Verify status enum values
    assert "all" in props["status"]["enum"]
    assert "accepted" in props["status"]["enum"]
    assert "deprecated" in props["status"]["enum"]


@pytest.mark.anyio
async def test_find_similar_code_schema(knowledge_client: AsyncClient) -> None:
    """find_similar_code requires code and accepts language and limit."""
    resp = await knowledge_client.get("/api/v1/tools")
    tools = resp.json()
    similar_tool = next(t for t in tools if t["name"] == "find_similar_code")
    props = similar_tool["input_schema"]["properties"]
    assert "code" in props
    assert "language" in props
    assert "limit" in props
    assert similar_tool["input_schema"]["required"] == ["code"]


@pytest.mark.anyio
async def test_get_best_practices_schema(knowledge_client: AsyncClient) -> None:
    """get_best_practices requires domain and accepts language and limit."""
    resp = await knowledge_client.get("/api/v1/tools")
    tools = resp.json()
    bp_tool = next(t for t in tools if t["name"] == "get_best_practices")
    props = bp_tool["input_schema"]["properties"]
    assert "domain" in props
    assert "language" in props
    assert "limit" in props
    assert bp_tool["input_schema"]["required"] == ["domain"]


@pytest.mark.anyio
async def test_call_unknown_knowledge_tool(knowledge_client: AsyncClient) -> None:
    """Calling a non-existent tool returns a structured error."""
    resp = await knowledge_client.post(
        "/api/v1/tools/call",
        json={"tool_name": "nonexistent_tool", "arguments": {}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tool_name"] == "nonexistent_tool"
    assert body["error"] is not None
    assert "Unknown tool" in body["error"]
    assert body["execution_time_ms"] == 0.0
