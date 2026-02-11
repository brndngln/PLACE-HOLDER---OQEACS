from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "runtime-manager"
    service_port: int = 9624
    version: str = "1.0.0"
    log_level: str = "info"
    log_format: str = "json"
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    litellm_url: str = "http://omni-litellm:4000"
    litellm_api_key: str = ""
    qdrant_url: str = "http://omni-qdrant:6333"
    qdrant_collection: str = "runtime-manager"
    langfuse_host: str = "http://omni-langfuse:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    mattermost_webhook_url: str = ""
    mattermost_channel: str = "omni-generation-intelligence"
    minio_endpoint: str = "omni-minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "gi-runtime-manager"
    minio_secure: bool = False
    gitea_url: str = "http://omni-gitea:3000"
    gitea_token: str = ""

    docker_socket: str = "/var/run/docker.sock"
    max_concurrent_sandboxes: int = 10
    default_timeout_seconds: int = 300
    default_memory_limit: str = "2g"
    default_cpu_limit: float = 2.0
    default_disk_limit: str = "1g"
    sandbox_network: str = "none"
    sandbox_ttl_seconds: int = 3600
    workspace_base: str = "/workspaces"
    runtime_image_prefix: str = "omni-runtime"
    max_output_bytes: int = 1048576
    max_file_size_bytes: int = 10485760

    analysis_workspace: str = "/app/data/analyses"
    max_concurrent_analyses: int = 3
    max_repo_size_mb: int = 500
    max_files_to_analyze: int = 5000
    profile_max_tokens: int = 4000
    profile_cache_ttl_hours: int = 24
    tree_sitter_timeout_ms: int = 5000
    synthesis_model: str = "qwen3-coder:30b"

    api_index_db_path: str = "/app/data/api_index.db"
    confidence_threshold: float = 0.8

    image_prefix: str = "omni-runtime"
    rebuild_schedule: str = "0 3 * * 0"
    max_concurrent_builds: int = 2
    build_timeout_seconds: int = 1800

    max_increment_lines: int = 200
    max_retries_per_increment: int = 3
    max_total_increments: int = 100
    generation_model: str = "devstral-2:123b"
    verification_timeout_seconds: int = 120

    classification_model: str = "qwen3-coder:30b"
    budget_pause_multiplier: float = 2.0
    cost_per_gpu_hour: float = 2.49
    cost_per_1k_tokens_local: float = 0.0

    @property
    def log_level_int(self) -> int:
        level = self.log_level.lower()
        return {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}.get(level, 20)


settings = Settings()
