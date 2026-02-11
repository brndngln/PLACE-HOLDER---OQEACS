from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ComponentSpec(BaseModel):
    name: str
    description: str
    props: list[str] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)
    accessibility_requirements: list[str] = Field(default_factory=list)


class GeneratedComponent(BaseModel):
    code: str
    framework: str
    a11y_score: float
    responsive: bool
    css: str


class DesignTokens(BaseModel):
    colors: dict[str, str] = Field(default_factory=dict)
    typography: dict[str, str] = Field(default_factory=dict)
    spacing: dict[str, str] = Field(default_factory=dict)
    breakpoints: dict[str, str] = Field(default_factory=dict)
    shadows: dict[str, str] = Field(default_factory=dict)


class WireframeRequest(BaseModel):
    description: str
    framework: str
    design_tokens: DesignTokens = Field(default_factory=DesignTokens)


class AccessibilityReport(BaseModel):
    score: float
    violations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
