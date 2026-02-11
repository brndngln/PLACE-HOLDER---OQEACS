from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DocGenerationRequest(BaseModel):
    code: str
    language: str
    doc_type: Literal["api", "readme", "architecture", "onboarding", "changelog"]


class DiagramSpec(BaseModel):
    type: Literal["mermaid", "plantuml"]
    content: str


class GeneratedDoc(BaseModel):
    content: str
    format: Literal["markdown", "html", "rst"] = "markdown"
    sections: list[str] = Field(default_factory=list)
    diagrams: list[DiagramSpec] = Field(default_factory=list)


class DocSyncCheck(BaseModel):
    file_path: str
    doc_path: str
    in_sync: bool
    stale_sections: list[str] = Field(default_factory=list)
