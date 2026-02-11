"""Pydantic v2 models for System 45 - Knowledge Freshness Service."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FeedCategory(str, Enum):
    """Categories for knowledge feeds."""

    GITHUB_RELEASES = "github_releases"
    SECURITY_ADVISORIES = "security_advisories"
    FRAMEWORK_CHANGELOGS = "framework_changelogs"
    BEST_PRACTICES = "best_practices"


class DeprecationSeverity(str, Enum):
    """Severity levels for deprecation warnings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedConfig(BaseModel):
    """Configuration for a monitored feed source."""

    id: str = Field(..., description="Unique identifier for the feed")
    name: str = Field(..., description="Human-readable feed name")
    url: str = Field(..., description="Feed URL")
    category: FeedCategory = Field(..., description="Feed category")
    enabled: bool = Field(default=True, description="Whether the feed is actively scanned")
    last_checked: Optional[datetime] = Field(
        default=None, description="Timestamp of last successful scan"
    )


class FeedConfigCreate(BaseModel):
    """Schema for creating a new feed configuration."""

    name: str = Field(..., min_length=1, max_length=256, description="Human-readable feed name")
    url: str = Field(..., min_length=1, description="Feed URL")
    category: FeedCategory = Field(..., description="Feed category")
    enabled: bool = Field(default=True, description="Whether the feed is actively scanned")


class KnowledgeUpdate(BaseModel):
    """A single knowledge update parsed from a feed."""

    id: str = Field(..., description="Unique identifier for the update")
    title: str = Field(..., description="Title of the update")
    summary: str = Field(default="", description="Summary or description of the update")
    url: str = Field(default="", description="Link to the original source")
    source: str = Field(..., description="Source feed name")
    category: FeedCategory = Field(..., description="Category of the update")
    published_at: datetime = Field(
        default_factory=datetime.utcnow, description="Publication timestamp"
    )
    relevance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="AI-computed relevance score"
    )
    is_breaking_change: bool = Field(
        default=False, description="Whether this is a breaking change"
    )
    is_deprecation: bool = Field(
        default=False, description="Whether this involves a deprecation"
    )
    affected_languages: list[str] = Field(
        default_factory=list, description="Programming languages affected"
    )


class ScanReport(BaseModel):
    """Report generated after a feed scan cycle."""

    total_updates: int = Field(default=0, description="Total updates discovered")
    relevant_updates: int = Field(default=0, description="Updates meeting relevance threshold")
    breaking_changes: list[KnowledgeUpdate] = Field(
        default_factory=list, description="Breaking change updates"
    )
    deprecations: list[KnowledgeUpdate] = Field(
        default_factory=list, description="Deprecation updates"
    )
    scan_duration_seconds: float = Field(
        default=0.0, description="Total scan duration in seconds"
    )
    scanned_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of scan completion"
    )


class DeprecationWarning(BaseModel):
    """A tracked deprecation warning."""

    package: str = Field(..., description="Affected package name")
    old_version: str = Field(default="", description="Deprecated version")
    new_version: str = Field(default="", description="Replacement version")
    deprecation_type: str = Field(
        default="api_change", description="Type of deprecation (api_change, removal, rename)"
    )
    migration_guide: str = Field(default="", description="Link or text for migration guidance")
    severity: DeprecationSeverity = Field(
        default=DeprecationSeverity.MEDIUM, description="Severity level"
    )
    detected_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the deprecation was detected"
    )


class WeeklyReport(BaseModel):
    """Weekly aggregated report of knowledge freshness."""

    week_start: datetime = Field(..., description="Start of the reporting week")
    week_end: datetime = Field(..., description="End of the reporting week")
    total_updates: int = Field(default=0, description="Total updates for the week")
    breaking_changes_count: int = Field(default=0, description="Number of breaking changes")
    deprecations_count: int = Field(default=0, description="Number of deprecations")
    top_updates: list[KnowledgeUpdate] = Field(
        default_factory=list, description="Top updates ranked by relevance"
    )
    freshness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall freshness score (0-100) for the knowledge base",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    service: str = Field(default="knowledge-freshness")
    version: str = Field(default="1.0.0")
    uptime_seconds: float = Field(default=0.0)
    checks: dict[str, str] = Field(default_factory=dict)
