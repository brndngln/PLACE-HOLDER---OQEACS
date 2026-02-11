"""
System 44 — MCP Analysis Server tool tests.

Validates the tool listing endpoint and verifies that the tool-call
endpoint handles unknown tools gracefully.  The measure_complexity tool
is tested end-to-end since it uses pure AST analysis without external
dependencies.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_analysis_tools(analysis_client: AsyncClient) -> None:
    """GET /api/v1/tools returns all four analysis tools."""
    resp = await analysis_client.get("/api/v1/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    assert len(tools) == 4

    names = {t["name"] for t in tools}
    assert names == {"analyze_code", "detect_antipatterns", "measure_complexity", "check_security"}


@pytest.mark.anyio
async def test_analysis_tool_definitions_have_schemas(analysis_client: AsyncClient) -> None:
    """Every analysis tool has non-empty input and output schemas."""
    resp = await analysis_client.get("/api/v1/tools")
    tools = resp.json()
    for tool in tools:
        assert "input_schema" in tool, f"{tool['name']} missing input_schema"
        assert "output_schema" in tool, f"{tool['name']} missing output_schema"
        assert tool["input_schema"], f"{tool['name']} has empty input_schema"
        assert tool["output_schema"], f"{tool['name']} has empty output_schema"
        assert tool["description"], f"{tool['name']} has empty description"


@pytest.mark.anyio
async def test_call_unknown_tool(analysis_client: AsyncClient) -> None:
    """Calling a non-existent tool returns an error in MCPToolResult."""
    resp = await analysis_client.post(
        "/api/v1/tools/call",
        json={"tool_name": "does_not_exist", "arguments": {}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tool_name"] == "does_not_exist"
    assert body["error"] is not None
    assert "Unknown tool" in body["error"]


@pytest.mark.anyio
async def test_measure_complexity_simple_function(analysis_client: AsyncClient) -> None:
    """measure_complexity returns correct metrics for a simple function."""
    code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
    resp = await analysis_client.post(
        "/api/v1/tools/call",
        json={"tool_name": "measure_complexity", "arguments": {"code": code}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tool_name"] == "measure_complexity"
    assert body["error"] is None
    result = body["result"]
    assert result["cyclomatic_complexity"] >= 1
    assert result["loc"] > 0
    assert result["sloc"] > 0
    assert len(result["functions"]) == 1
    assert result["functions"][0]["name"] == "add"


@pytest.mark.anyio
async def test_measure_complexity_branching(analysis_client: AsyncClient) -> None:
    """measure_complexity correctly counts branches."""
    code = '''
def classify(x: int) -> str:
    if x > 0:
        if x > 100:
            return "large"
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
'''
    resp = await analysis_client.post(
        "/api/v1/tools/call",
        json={"tool_name": "measure_complexity", "arguments": {"code": code}},
    )
    assert resp.status_code == 200
    body = resp.json()
    result = body["result"]
    # Should have higher complexity due to multiple branches
    assert result["cyclomatic_complexity"] >= 4
    assert len(result["functions"]) == 1
    assert result["functions"][0]["name"] == "classify"


@pytest.mark.anyio
async def test_measure_complexity_syntax_error(analysis_client: AsyncClient) -> None:
    """measure_complexity handles syntax errors gracefully."""
    resp = await analysis_client.post(
        "/api/v1/tools/call",
        json={
            "tool_name": "measure_complexity",
            "arguments": {"code": "def broken(:\n  pass"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    result = body["result"]
    assert result["cyclomatic_complexity"] == -1
    assert "error" in result


@pytest.mark.anyio
async def test_measure_complexity_non_python(analysis_client: AsyncClient) -> None:
    """measure_complexity returns a note for non-Python languages."""
    resp = await analysis_client.post(
        "/api/v1/tools/call",
        json={
            "tool_name": "measure_complexity",
            "arguments": {"code": "fn main() {}", "language": "rust"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    result = body["result"]
    assert result["cyclomatic_complexity"] == -1
    assert "note" in result


@pytest.mark.anyio
async def test_tool_call_returns_execution_time(analysis_client: AsyncClient) -> None:
    """Tool call results include positive execution_time_ms."""
    resp = await analysis_client.post(
        "/api/v1/tools/call",
        json={
            "tool_name": "measure_complexity",
            "arguments": {"code": "x = 1"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["execution_time_ms"] >= 0.0
