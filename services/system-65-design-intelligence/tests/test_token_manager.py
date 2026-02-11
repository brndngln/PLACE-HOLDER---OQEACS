from __future__ import annotations

from src.models import DesignTokens
from src.services.token_manager import TokenManager


def test_get_tokens() -> None:
    t = TokenManager().get_tokens()
    assert "primary" in t.colors


def test_store_tokens() -> None:
    mgr = TokenManager()
    out = mgr.store_tokens(DesignTokens(colors={"primary": "#000"}))
    assert out.colors["primary"] == "#000"


def test_validate_defaults() -> None:
    mgr = TokenManager()
    out = mgr.validate_tokens(DesignTokens())
    assert "primary" in out.colors
