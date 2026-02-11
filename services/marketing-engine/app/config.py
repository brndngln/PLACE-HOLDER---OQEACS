from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", env_file_encoding="utf-8", extra="ignore")
    service_name: str = "marketing-engine"
    service_port: int = 9640
    version: str = "1.0.0"
    log_level: str = "info"
    log_format: str = "json"
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    litellm_url: str = "http://omni-litellm:4000"
    litellm_api_key: str = ""
    qdrant_url: str = "http://omni-qdrant:6333"
    qdrant_collection: str = "marketing-engine"
    langfuse_host: str = "http://omni-langfuse:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    mattermost_webhook_url: str = ""
    mattermost_channel: str = "omni-generation-intelligence"
    minio_endpoint: str = "omni-minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "marketing-engine-assets"
    minio_secure: bool = False

    content_generation_model: str = "devstral-2:123b"
    copy_variant_count: int = 5
    max_email_batch_size: int = 1000
    max_campaigns_active: int = 50
    ab_test_min_sample_size: int = 100
    ab_test_confidence_level: float = 0.95
    lead_scoring_model: str = "qwen3-coder:30b"
    competitor_scan_interval_hours: int = 24
    content_calendar_lookahead_days: int = 90
    landing_page_output_path: str = "/app/data/landing_pages"
    lead_magnet_storage_bucket: str = "marketing-lead-magnets"
    email_template_bucket: str = "marketing-email-templates"
    asset_bucket: str = "marketing-assets"
    listmonk_url: str = "http://omni-listmonk:9000"
    listmonk_api_user: str = ""
    listmonk_api_password: str = ""

    @property
    def log_level_int(self) -> int:
        return {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}.get(self.log_level.lower(), 20)


settings = Settings()
