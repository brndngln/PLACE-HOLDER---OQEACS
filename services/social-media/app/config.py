from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", env_file_encoding="utf-8", extra="ignore")
    service_name: str = "social-media"
    service_port: int = 9641
    version: str = "1.0.0"
    log_level: str = "info"
    log_format: str = "json"
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    litellm_url: str = "http://omni-litellm:4000"
    litellm_api_key: str = ""
    qdrant_url: str = "http://omni-qdrant:6333"
    qdrant_collection: str = "social-media"
    langfuse_host: str = "http://omni-langfuse:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    mattermost_webhook_url: str = ""
    mattermost_channel: str = "omni-generation-intelligence"
    minio_endpoint: str = "omni-minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "social-media-assets"
    minio_secure: bool = False

    marketing_engine_url: str = "http://omni-marketing-engine:9640"
    content_generation_model: str = "devstral-2:123b"
    post_variants_per_platform: int = 3
    max_scheduled_posts: int = 1000
    optimal_time_window_minutes: int = 30
    trend_scan_interval_minutes: int = 60
    competitor_scan_interval_hours: int = 6
    analytics_aggregation_interval_minutes: int = 30
    engagement_response_scan_minutes: int = 15
    max_hashtags_per_post: int = 30
    viral_threshold_engagement_rate: float = 0.05
    growth_milestone_intervals: list[int] = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000, 5000000, 10000000, 25000000, 50000000, 100000000]
    rss_feed_urls: list[str] = []
    news_scan_keywords: list[str] = []
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    instagram_access_token: str = ""
    youtube_api_key: str = ""
    tiktok_access_token: str = ""
    facebook_page_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    threads_access_token: str = ""
    bluesky_handle: str = ""
    bluesky_app_password: str = ""

    @property
    def log_level_int(self) -> int:
        return {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}.get(self.log_level.lower(), 20)


settings = Settings()
