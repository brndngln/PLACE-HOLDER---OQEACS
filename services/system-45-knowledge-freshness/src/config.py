"""Configuration for System 45 - Knowledge Freshness Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    SERVICE_NAME: str = "knowledge-freshness"
    SERVICE_PORT: int = 8330
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_freshness"

    # Redis
    REDIS_URL: str = "redis://omni-redis:6379/10"

    # Qdrant vector store
    QDRANT_URL: str = "http://omni-qdrant:6333"

    # LiteLLM AI gateway
    LITELLM_URL: str = "http://omni-litellm:4000"

    # Mattermost webhook
    MATTERMOST_WEBHOOK_URL: str = "http://omni-mattermost-webhook:8066"

    # Scan intervals
    SCAN_INTERVAL_HOURS: int = 6
    SECURITY_SCAN_INTERVAL_HOURS: int = 1

    # GitHub token (optional, raises rate limits)
    GITHUB_TOKEN: str = ""

    # Qdrant collection name
    QDRANT_COLLECTION: str = "knowledge_freshness"

    # Relevance threshold for storing updates
    RELEVANCE_THRESHOLD: float = 0.7

    # Similarity threshold for deduplication
    SIMILARITY_THRESHOLD: float = 0.95

    model_config = {"env_prefix": "", "case_sensitive": True}


settings = Settings()
