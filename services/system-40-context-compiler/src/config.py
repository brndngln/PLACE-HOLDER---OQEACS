"""System 40: Context Compiler — Configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "context-compiler"
    SERVICE_PORT: int = 8325
    DATABASE_URL: str = "postgresql://omni:omni@omni-postgres:5432/omni_quantum"
    REDIS_URL: str = "redis://omni-redis:6379/0"
    QDRANT_URL: str = "http://omni-qdrant:6333"
    MATTERMOST_WEBHOOK_URL: str = ""
    VAULT_ADDR: str = "http://omni-vault:8200"
    LITELLM_URL: str = "http://omni-litellm:4000"
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus"
    DEFAULT_TOKEN_BUDGET: int = 128000
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    COMPRESSION_MODEL: str = "qwen2.5-72b"

    model_config = {"env_prefix": "", "case_sensitive": True}
