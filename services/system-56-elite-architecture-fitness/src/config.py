'''Configuration for omni-elite-architecture-fitness.'''
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    '''Runtime settings loaded from environment variables.'''

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = Field(default="omni-elite-architecture-fitness", alias="SERVICE_NAME")
    port: int = Field(default=9901, alias="SERVICE_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql://omni:omni@omni-postgres:5432/omni_quantum",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://omni-redis:6379/0", alias="REDIS_URL")
    qdrant_url: str = Field(default="http://omni-qdrant:6333", alias="QDRANT_URL")
    litellm_url: str = Field(default="http://omni-litellm:4000", alias="LITELLM_URL")
    langfuse_url: str = Field(default="http://omni-langfuse:3000", alias="LANGFUSE_URL")
    vault_addr: str = Field(default="http://omni-vault:8200", alias="VAULT_ADDR")
    mattermost_webhook_url: str | None = Field(default=None, alias="MATTERMOST_WEBHOOK_URL")
    omi_bridge_url: str | None = Field(default="http://omni-omi-bridge:9700", alias="OMI_BRIDGE_URL")
