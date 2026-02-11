from __future__ import annotations

from src.models import DesignTokens


class TokenManager:
    def __init__(self) -> None:
        self._tokens = DesignTokens(
            colors={"primary": "#0a66ff", "background": "#ffffff", "text": "#111111"},
            typography={"fontFamily": "Inter", "base": "16px"},
            spacing={"sm": "8px", "md": "16px", "lg": "24px"},
            breakpoints={"sm": "640px", "md": "768px", "lg": "1024px"},
            shadows={"card": "0 6px 24px rgba(0,0,0,0.12)"},
        )

    def store_tokens(self, tokens: DesignTokens) -> DesignTokens:
        self._tokens = self.validate_tokens(tokens)
        return self._tokens

    def get_tokens(self) -> DesignTokens:
        return self._tokens

    def validate_tokens(self, tokens: DesignTokens) -> DesignTokens:
        if "primary" not in tokens.colors:
            tokens.colors["primary"] = "#0a66ff"
        if "base" not in tokens.typography:
            tokens.typography["base"] = "16px"
        return tokens
