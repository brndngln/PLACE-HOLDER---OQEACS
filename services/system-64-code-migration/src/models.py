from __future__ import annotations

from pydantic import BaseModel, Field


class MigrationRequest(BaseModel):
    source_framework: str
    target_framework: str
    code: str
    language: str


class MigrationRule(BaseModel):
    from_pattern: str
    to_pattern: str
    description: str
    auto_applicable: bool = True


class MigrationResult(BaseModel):
    migrated_code: str
    changes_made: list[str] = Field(default_factory=list)
    breaking_changes: list[str] = Field(default_factory=list)
    manual_review_needed: list[str] = Field(default_factory=list)


class SupportedMigration(BaseModel):
    source: str
    target: str
    complexity: str
    rule_count: int
