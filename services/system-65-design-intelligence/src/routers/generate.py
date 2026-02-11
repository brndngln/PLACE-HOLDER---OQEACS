from __future__ import annotations

from fastapi import APIRouter

from src.models import AccessibilityReport, ComponentSpec, DesignTokens, WireframeRequest
from src.services.accessibility_checker import AccessibilityChecker
from src.services.component_generator import ComponentGenerator
from src.services.token_manager import TokenManager

router = APIRouter(prefix="/api/v1", tags=["design"])
_tokens = TokenManager()


@router.post("/generate")
def generate(payload: dict):
    spec = ComponentSpec(**payload["spec"])
    framework = payload.get("framework", "react")
    tokens = _tokens.get_tokens()
    return ComponentGenerator().generate(spec, framework, tokens)


@router.post("/check-a11y", response_model=AccessibilityReport)
def check_a11y(payload: dict) -> AccessibilityReport:
    return AccessibilityChecker().check(payload.get("code", ""))


@router.get("/tokens")
def get_tokens() -> DesignTokens:
    return _tokens.get_tokens()


@router.post("/tokens")
def set_tokens(tokens: DesignTokens):
    return _tokens.store_tokens(tokens)
