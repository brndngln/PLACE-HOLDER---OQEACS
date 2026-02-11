"""Tests for tool registry and tool selection logic."""
from src.models import VerificationTool
from src.services.tool_registry import (
    LANGUAGE_TO_TOOL,
    TOOL_DEFINITIONS,
    list_tools,
    select_tool,
)
import pytest


def test_select_tool_python():
    assert select_tool("python") == "crosshair"


def test_select_tool_c():
    assert select_tool("c") == "cbmc"


def test_select_tool_rust():
    assert select_tool("rust") == "kani"


def test_select_tool_override():
    assert select_tool("python", VerificationTool.TLA_PLUS) == "tla_plus"


def test_select_tool_unknown_raises():
    with pytest.raises(ValueError, match="No verification tool"):
        select_tool("brainfuck")


def test_all_tools_have_definitions():
    for tool_id in LANGUAGE_TO_TOOL.values():
        assert tool_id in TOOL_DEFINITIONS, f"Missing definition for {tool_id}"


def test_list_tools_returns_all():
    tools = list_tools()
    assert len(tools) == len(TOOL_DEFINITIONS)
    for tool in tools:
        assert tool.name
        assert tool.purpose
        assert len(tool.supported_languages) > 0


def test_tool_definitions_have_required_fields():
    required = {"binary", "command_template", "purpose", "input_ext", "languages"}
    for tool_id, defn in TOOL_DEFINITIONS.items():
        for field in required:
            assert field in defn, f"Tool {tool_id} missing field {field}"
