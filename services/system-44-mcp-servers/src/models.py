"""
System 44 — Pydantic v2 data models.

Every model uses ``model_config = ConfigDict(from_attributes=True)`` so
ORM rows or plain dicts can be loaded with ``Model.model_validate()``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── MCP Protocol models ──────────────────────────────────────────────


class MCPToolDefinition(BaseModel):
    """Describes a single MCP tool exposed by a server."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Human-readable description of the tool")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema describing the tool's input parameters",
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema describing the tool's output",
    )


class MCPToolCall(BaseModel):
    """Request to invoke a specific MCP tool."""

    model_config = ConfigDict(from_attributes=True)

    tool_name: str = Field(..., description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value arguments for the tool",
    )


class MCPToolResult(BaseModel):
    """Result from a single MCP tool invocation."""

    model_config = ConfigDict(from_attributes=True)

    tool_name: str = Field(..., description="Name of the invoked tool")
    result: Any = Field(default=None, description="Tool output on success")
    error: str | None = Field(default=None, description="Error message on failure")
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Wall-clock execution time in milliseconds",
    )


# ── Analysis Server models ───────────────────────────────────────────


class AnalysisRequest(BaseModel):
    """Request payload for code analysis tools."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., min_length=1, description="Source code to analyse")
    language: str = Field(
        default="python", description="Programming language of the source code"
    )
    analysis_type: str = Field(
        default="full",
        description="Type of analysis: full | security | complexity | antipatterns",
    )


class AnalysisResult(BaseModel):
    """Response from code analysis tools."""

    model_config = ConfigDict(from_attributes=True)

    issues: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected issues with severity, line, and message",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Calculated code metrics (complexity, LOC, etc.)",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable improvement suggestions",
    )


# ── Test Server models ───────────────────────────────────────────────


class TestGenRequest(BaseModel):
    """Request payload for test generation tools."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., min_length=1, description="Source code to generate tests for")
    language: str = Field(default="python", description="Programming language")
    framework: str = Field(
        default="pytest", description="Test framework to target (pytest, jest, go-test, etc.)"
    )


class TestGenResult(BaseModel):
    """Response from test generation tools."""

    model_config = ConfigDict(from_attributes=True)

    tests: str = Field(default="", description="Generated test source code")
    coverage_estimate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Estimated code coverage percentage (0-100)",
    )


# ── Deploy Server models ─────────────────────────────────────────────


class DeployRequest(BaseModel):
    """Request payload for deployment tools."""

    model_config = ConfigDict(from_attributes=True)

    project_id: str = Field(..., description="Project or service identifier")
    environment: str = Field(
        default="staging",
        description="Target environment: staging | production | preview",
    )
    strategy: str = Field(
        default="rolling",
        description="Deployment strategy: rolling | blue-green | canary",
    )


class DeployResult(BaseModel):
    """Response from deployment tools."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        default="pending",
        description="Deployment status: pending | in_progress | success | failed | rolled_back",
    )
    url: str | None = Field(default=None, description="Deployment URL if available")
    logs: list[str] = Field(
        default_factory=list,
        description="Deployment log entries",
    )


# ── Knowledge Server models ──────────────────────────────────────────


class KnowledgeQuery(BaseModel):
    """Request payload for knowledge base queries."""

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., min_length=1, description="Natural-language search query")
    collections: list[str] = Field(
        default_factory=lambda: ["engineering_docs"],
        description="Qdrant collections to search",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )


class KnowledgeResult(BaseModel):
    """Response from knowledge base queries."""

    model_config = ConfigDict(from_attributes=True)

    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Matching documents with score and payload",
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total number of matching documents",
    )
