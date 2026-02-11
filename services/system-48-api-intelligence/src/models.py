"""Pydantic v2 models for System 48B: Real-Time API Intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PackageRegistry(BaseModel):
    """Represents a tracked package from any supported registry."""

    name: str = Field(..., description="Package name")
    registry: Literal["pypi", "npm", "crates", "go", "maven"] = Field(
        ..., description="Source registry"
    )
    current_version: str = Field(..., description="Currently installed version")
    latest_version: str = Field(..., description="Latest available version")
    is_outdated: bool = Field(default=False, description="Whether an update is available")
    breaking_changes: list[str] = Field(
        default_factory=list, description="Known breaking changes between versions"
    )
    deprecations: list[str] = Field(
        default_factory=list, description="Deprecated APIs or features"
    )
    security_advisories: list[str] = Field(
        default_factory=list, description="Security advisories (CVEs)"
    )
    last_checked: datetime = Field(
        default_factory=datetime.utcnow, description="Last scan timestamp"
    )


class APIChange(BaseModel):
    """Represents a single API change between two versions of a package."""

    package: str = Field(..., description="Package name")
    from_version: str = Field(..., description="Previous version")
    to_version: str = Field(..., description="New version")
    change_type: Literal["breaking", "deprecation", "new_feature", "bugfix", "security"] = Field(
        ..., description="Type of change"
    )
    description: str = Field(..., description="Human-readable description of the change")
    migration_guide: str = Field(
        default="", description="Step-by-step migration instructions"
    )
    affected_symbols: list[str] = Field(
        default_factory=list, description="Functions, classes, or modules affected"
    )


class CompatibilityMatrix(BaseModel):
    """Compatibility check result between two packages at specific versions."""

    package_a: str = Field(..., description="First package name")
    version_a: str = Field(..., description="First package version")
    package_b: str = Field(..., description="Second package name")
    version_b: str = Field(..., description="Second package version")
    compatible: bool = Field(..., description="Whether the two are compatible")
    notes: str = Field(default="", description="Additional compatibility notes")


class DependencyScanRequest(BaseModel):
    """Request to scan a project's dependencies."""

    project_path: str = Field(..., description="Path to project root or lockfile")
    lockfile_type: Literal[
        "requirements.txt", "package-lock.json", "Cargo.lock", "go.sum", "pom.xml"
    ] = Field(..., description="Type of lockfile to parse")


class UpgradePlan(BaseModel):
    """A planned upgrade for a single package."""

    package: str = Field(..., description="Package to upgrade")
    from_v: str = Field(..., description="Current version")
    to_v: str = Field(..., description="Target version")
    risk: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Risk level of the upgrade"
    )
    also_upgrade: list[str] = Field(
        default_factory=list,
        description="Packages that must also be upgraded for compatibility",
    )
    migration_steps: list[str] = Field(
        default_factory=list, description="Ordered migration instructions"
    )


class ScanResult(BaseModel):
    """Complete result of a dependency scan."""

    packages: list[PackageRegistry] = Field(
        default_factory=list, description="All scanned packages"
    )
    total_outdated: int = Field(default=0, description="Number of outdated packages")
    total_breaking: int = Field(
        default=0, description="Number of packages with breaking changes"
    )
    total_security: int = Field(
        default=0, description="Number of packages with security advisories"
    )
    upgrade_plan: list[UpgradePlan] = Field(
        default_factory=list, description="Recommended upgrade plan"
    )
    scanned_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the scan was performed"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    service: str = Field(default="omni-api-intelligence")
    version: str = Field(default="1.0.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PackageQuery(BaseModel):
    """Query parameters for looking up a single package."""

    registry: Literal["pypi", "npm", "crates", "go", "maven"] = Field(
        default="pypi", description="Registry to query"
    )
    current_version: str = Field(
        default="0.0.0", description="Currently installed version for comparison"
    )
