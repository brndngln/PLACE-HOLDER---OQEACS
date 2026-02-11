"""Pydantic v2 models for the Semantic Code Understanding Engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---


class EntityType(str, Enum):
    """Types of code entities that can be extracted."""

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    VARIABLE = "variable"
    IMPORT = "import"


class RelationshipType(str, Enum):
    """Types of relationships between code entities."""

    CALLS = "calls"
    IMPORTS = "imports"
    INHERITS = "inherits"
    OVERRIDES = "overrides"
    USES = "uses"
    RETURNS = "returns"
    RAISES = "raises"
    DECORATES = "decorates"


class AnalysisDepth(str, Enum):
    """Depth levels for codebase analysis."""

    SHALLOW = "shallow"
    STANDARD = "standard"
    FULL = "full"


# --- Core Entities ---


class CodeEntity(BaseModel):
    """Represents a single code entity extracted from source code."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Name of the code entity")
    entity_type: EntityType = Field(..., description="Type of entity")
    file_path: str = Field(..., description="File path relative to repo root")
    line_start: int = Field(..., ge=1, description="Starting line number")
    line_end: int = Field(..., ge=1, description="Ending line number")
    signature: str = Field(default="", description="Function/method signature or class declaration")
    docstring: str = Field(default="", description="Extracted docstring or documentation comment")
    complexity: int = Field(default=1, ge=1, description="Cyclomatic complexity estimate")
    language: str = Field(default="python", description="Source language")
    parent_id: str | None = Field(default=None, description="Parent entity ID for nested entities")
    decorators: list[str] = Field(default_factory=list, description="Applied decorators")
    annotations: dict[str, str] = Field(default_factory=dict, description="Type annotations")


class Relationship(BaseModel):
    """A directed relationship between two code entities."""

    source_id: str = Field(..., description="ID of the source entity")
    target_id: str = Field(..., description="ID of the target entity")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=10.0, description="Relationship strength weight")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional relationship metadata")


class SemanticGraph(BaseModel):
    """Complete semantic graph of a codebase."""

    repo_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entities: list[CodeEntity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    file_count: int = Field(default=0, ge=0, description="Number of files analyzed")
    total_entities: int = Field(default=0, ge=0, description="Total entities extracted")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    languages: list[str] = Field(default_factory=list, description="Languages found in the repo")
    centrality_scores: dict[str, float] = Field(
        default_factory=dict, description="Entity ID to centrality score mapping"
    )


# --- Request Models ---


class AnalysisRequest(BaseModel):
    """Request to analyze a codebase and build a semantic graph."""

    repo_path: str = Field(..., description="Path to the repository root")
    languages: list[str] = Field(
        default_factory=lambda: ["python"],
        description="Languages to analyze",
    )
    depth: AnalysisDepth = Field(default=AnalysisDepth.FULL, description="Analysis depth")
    include_tests: bool = Field(default=True, description="Whether to include test files")


class ImpactAnalysisRequest(BaseModel):
    """Request for change impact analysis."""

    file_path: str = Field(..., description="Path to the file being changed")
    function_name: str = Field(..., description="Name of the function being changed")
    change_description: str = Field(
        default="", description="Description of the intended change"
    )
    repo_id: str | None = Field(
        default=None, description="Existing graph repo_id to use; builds new graph if None"
    )


class CodeMeaningRequest(BaseModel):
    """Request to extract deep meaning from a code snippet."""

    code: str = Field(..., min_length=1, description="Source code to analyze")
    language: str = Field(default="python", description="Programming language of the code")
    context: str = Field(
        default="", description="Additional context about the code's role in the system"
    )


# --- Response Models ---


class AffectedEntity(BaseModel):
    """An entity affected by a proposed change."""

    entity_id: str
    name: str
    entity_type: EntityType
    file_path: str
    distance: int = Field(description="Graph distance from the changed entity")
    impact_type: str = Field(description="How this entity is affected (e.g., direct caller, transitive)")


class BreakingChange(BaseModel):
    """A predicted breaking change caused by a modification."""

    entity_id: str
    entity_name: str
    file_path: str
    reason: str = Field(description="Why this would break")
    severity: str = Field(description="high, medium, or low")
    suggested_fix: str = Field(default="", description="How to resolve the breaking change")


class SuggestedTest(BaseModel):
    """A test that should be run or written in response to a change."""

    test_name: str
    test_file: str
    reason: str
    exists: bool = Field(description="Whether this test already exists")
    priority: str = Field(default="medium", description="high, medium, or low")


class ImpactReport(BaseModel):
    """Complete impact analysis report for a proposed change."""

    affected_entities: list[AffectedEntity] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall risk score 0-1")
    breaking_changes: list[BreakingChange] = Field(default_factory=list)
    suggested_tests: list[SuggestedTest] = Field(default_factory=list)
    analysis_summary: str = Field(default="", description="Human-readable summary")
    total_affected: int = Field(default=0)
    max_depth: int = Field(default=0, description="Maximum dependency chain depth reached")


class CodeMeaning(BaseModel):
    """Deep semantic understanding of a code snippet."""

    summary: str = Field(description="One-paragraph summary of what this code does")
    purpose: str = Field(description="The higher-level purpose and design intent")
    side_effects: list[str] = Field(
        default_factory=list,
        description="Side effects: I/O, mutations, network, DB writes",
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="Discovered preconditions, postconditions, loop invariants",
    )
    implicit_contracts: list[str] = Field(
        default_factory=list,
        description="Unstated assumptions and contracts with callers/callees",
    )
    complexity_assessment: str = Field(
        default="", description="Assessment of algorithmic and structural complexity"
    )


# --- Health / Status ---


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "omni-semantic-code"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphSummary(BaseModel):
    """Summary view of a stored semantic graph."""

    repo_id: str
    file_count: int
    total_entities: int
    total_relationships: int
    languages: list[str]
    generated_at: datetime
    top_central_entities: list[dict[str, Any]] = Field(default_factory=list)
