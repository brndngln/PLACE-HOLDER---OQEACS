from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HistoryEntry(BaseModel):
    commit_hash: str
    author: str
    date: datetime
    change_type: str
    message: str
    diff_summary: str


class CodeHistory(BaseModel):
    file_path: str
    function_name: str
    history: list[HistoryEntry] = Field(default_factory=list)


class CodeBiography(BaseModel):
    function_name: str
    file_path: str
    created_date: datetime
    created_by: str
    total_changes: int
    linked_issues: list[str]
    purpose: str
    workarounds: list[str]


class DeletionRisk(BaseModel):
    file_path: str
    function_name: str
    risk_level: str
    dependents_count: int
    last_used: str
    reason: str
