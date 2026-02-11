from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DependencyNode(BaseModel):
    name: str
    version: str
    ecosystem: str
    direct: bool = False


class DependencyTree(BaseModel):
    id: str
    nodes: list[DependencyNode]
    edges: list[tuple[str, str]]
    has_cycles: bool


class VulnerabilityInfo(BaseModel):
    package: str
    version: str
    cve: str
    severity: Literal["low", "medium", "high", "critical"]
    summary: str


class LicenseInfo(BaseModel):
    package: str
    license: str
    compatible: bool
    notes: str = ""


class UpgradePath(BaseModel):
    package: str
    from_version: str
    to_version: str
    risk: str


class SBOMDocument(BaseModel):
    bom_format: str = "CycloneDX"
    spec_version: str = "1.5"
    components: list[dict]


class ScanRequest(BaseModel):
    lockfile_path: str


class ScanResult(BaseModel):
    tree: DependencyTree
    vulnerabilities: list[VulnerabilityInfo] = Field(default_factory=list)
    licenses: list[LicenseInfo] = Field(default_factory=list)
