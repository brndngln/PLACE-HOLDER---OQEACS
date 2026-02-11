"""Configuration for the Semantic Code Understanding Engine."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    SERVICE_NAME: str = "omni-semantic-code"
    SERVICE_PORT: int = 9651
    DATABASE_URL: str = "postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_semantic_code"
    REDIS_URL: str = "redis://omni-redis:6379/15"
    QDRANT_URL: str = "http://omni-qdrant:6333"
    LITELLM_URL: str = "http://omni-litellm:4000"
    MATTERMOST_WEBHOOK_URL: str = "http://omni-mattermost:8065/hooks/semantic-code"
    TREE_SITTER_LANGUAGES: str = "python,typescript,go,rust,java"
    LOG_LEVEL: str = "INFO"
    DEFAULT_MODEL: str = "gpt-4o"
    ANALYSIS_TIMEOUT_SECONDS: int = 300
    MAX_FILE_SIZE_KB: int = 512

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported tree-sitter languages."""
        return [lang.strip() for lang in self.TREE_SITTER_LANGUAGES.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
