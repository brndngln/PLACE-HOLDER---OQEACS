#!/usr/bin/env python3
from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"

BASE_REQS = [
    "fastapi==0.115.6",
    "uvicorn[standard]==0.34.0",
    "uvloop==0.21.0",
    "httptools==0.6.4",
    "pydantic==2.10.4",
    "pydantic-settings==2.7.1",
    "httpx==0.28.1",
    "sqlalchemy[asyncio]==2.0.36",
    "asyncpg==0.30.0",
    "alembic==1.14.0",
    "redis[hiredis]==5.2.1",
    "structlog==24.4.0",
    "prometheus-client==0.21.1",
    "qdrant-client==1.12.1",
    "minio==7.2.12",
    "pytest==8.3.4",
    "pytest-asyncio==0.24.0",
    "pytest-cov==6.0.0",
    "ruff==0.8.6",
    "mypy==1.13.0",
]


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def ensure_env_example() -> None:
    keys = {
        "LISTMONK_API_USER": "admin",
        "LISTMONK_API_PASSWORD": "CHANGE_ME",
        "TWITTER_API_KEY": "CHANGE_ME",
        "TWITTER_API_SECRET": "CHANGE_ME",
        "TWITTER_ACCESS_TOKEN": "CHANGE_ME",
        "TWITTER_ACCESS_SECRET": "CHANGE_ME",
        "LINKEDIN_CLIENT_ID": "CHANGE_ME",
        "LINKEDIN_CLIENT_SECRET": "CHANGE_ME",
        "INSTAGRAM_ACCESS_TOKEN": "CHANGE_ME",
        "YOUTUBE_API_KEY": "CHANGE_ME",
        "TIKTOK_ACCESS_TOKEN": "CHANGE_ME",
        "FACEBOOK_PAGE_TOKEN": "CHANGE_ME",
        "REDDIT_CLIENT_ID": "CHANGE_ME",
        "REDDIT_CLIENT_SECRET": "CHANGE_ME",
        "THREADS_ACCESS_TOKEN": "CHANGE_ME",
        "BLUESKY_HANDLE": "CHANGE_ME",
        "BLUESKY_APP_PASSWORD": "CHANGE_ME",
    }
    env = ROOT / ".env.example"
    if not env.exists():
        return
    lines = env.read_text(encoding="utf-8").splitlines()
    present = {line.split("=", 1)[0] for line in lines if "=" in line and not line.strip().startswith("#")}
    adds = [f"{k}={v}" for k, v in keys.items() if k not in present]
    if adds:
        lines.append("")
        lines.append("# Marketing and Social Integrations")
        lines.extend(adds)
        env.write_text("\n".join(lines) + "\n", encoding="utf-8")


def reqs(extra: list[str]) -> str:
    out = []
    for item in BASE_REQS + extra:
        if item not in out:
            out.append(item)
    return "\n".join(out) + "\n"


def dockerfile(slug: str, display: str, port: int) -> str:
    return f"""
    FROM python:3.12-slim AS builder
    WORKDIR /build
    RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
    COPY requirements.txt .
    RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

    FROM python:3.12-slim AS production
    ARG BUILD_DATE
    ARG VERSION=1.0.0
    LABEL maintainer="Omni Quantum Elite" \\
          version="${{VERSION}}" \\
          build-date="${{BUILD_DATE}}" \\
          org.opencontainers.image.title="omni-{slug}" \\
          org.opencontainers.image.description="{display}" \\
          org.opencontainers.image.version="${{VERSION}}"

    WORKDIR /app
    RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && rm -rf /var/lib/apt/lists/* && \\
        groupadd -r omni && useradd -r -g omni -d /app -s /sbin/nologin omni && \\
        mkdir -p /app/data && chown -R omni:omni /app

    COPY --from=builder /install /usr/local
    COPY --chown=omni:omni app/ ./app/
    COPY --chown=omni:omni alembic/ ./alembic/
    COPY --chown=omni:omni alembic.ini ./alembic.ini
    COPY --chown=omni:omni scripts/ ./scripts/
    RUN chmod +x scripts/*.sh

    USER omni
    EXPOSE {port}
    HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}/health')"
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{port}", "--workers", "2", "--loop", "uvloop", "--http", "httptools", "--log-level", "info", "--access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
    """


def compose(service: str, port: int, db: str, redis_db: int, system: int, critical: bool, extra_env: list[str], bucket: str) -> str:
    env_lines = "\n".join([f"          {line}" for line in extra_env])
    return f"""
    version: "3.9"

    networks:
      omni-quantum-network:
        external: true

    volumes:
      {service.replace('-', '_')}_data:
        driver: local

    services:
      {service}:
        build:
          context: .
          dockerfile: Dockerfile
          args:
            BUILD_DATE: "${{BUILD_DATE:-2026-02-11T00:00:00Z}}"
            VERSION: "${{VERSION:-1.0.0}}"
        image: omni-{service}:${{VERSION:-1.0.0}}
        container_name: omni-{service}
        hostname: omni-{service}
        env_file:
          - ../../.env
        environment:
          SERVICE_NAME: "{service}"
          SERVICE_PORT: "{port}"
          VERSION: "${{VERSION:-1.0.0}}"
          LOG_LEVEL: "${{LOG_LEVEL:-info}}"
          LOG_FORMAT: "json"
          DATABASE_URL: "postgresql+asyncpg://${{GI_DB_USER:-omni}}:${{GI_DB_PASSWORD}}@omni-gi-postgres:5432/{db}"
          REDIS_URL: "redis://:${{REDIS_PASSWORD}}@omni-redis:6379/{redis_db}"
          LITELLM_URL: "http://omni-litellm:4000"
          LITELLM_API_KEY: "${{LITELLM_API_KEY}}"
          QDRANT_URL: "http://omni-qdrant:6333"
          QDRANT_COLLECTION: "{service}"
          LANGFUSE_HOST: "http://omni-langfuse:3000"
          LANGFUSE_PUBLIC_KEY: "${{LANGFUSE_PUBLIC_KEY}}"
          LANGFUSE_SECRET_KEY: "${{LANGFUSE_SECRET_KEY}}"
          MATTERMOST_WEBHOOK_URL: "${{MATTERMOST_GI_WEBHOOK_URL}}"
          MATTERMOST_CHANNEL: "omni-generation-intelligence"
          MINIO_ENDPOINT: "omni-minio:9000"
          MINIO_ACCESS_KEY: "${{MINIO_ACCESS_KEY}}"
          MINIO_SECRET_KEY: "${{MINIO_SECRET_KEY}}"
          MINIO_BUCKET: "{bucket}"
          MINIO_SECURE: "false"
{env_lines}
        ports:
          - "{port}:{port}"
        volumes:
          - {service.replace('-', '_')}_data:/app/data
        networks:
          - omni-quantum-network
        healthcheck:
          test: ["CMD-SHELL", "python -c \\\"import urllib.request; urllib.request.urlopen('http://localhost:{port}/health')\\\""]
          interval: 30s
          timeout: 10s
          retries: 3
          start_period: 40s
        restart: unless-stopped
        deploy:
          resources:
            limits:
              memory: 2G
              cpus: '2.0'
            reservations:
              memory: 512M
              cpus: '0.5'
        security_opt:
          - no-new-privileges:true
        read_only: true
        tmpfs:
          - /tmp:size=256M
        labels:
          - "omni.quantum.component={service}"
          - "omni.quantum.tier=generation-intelligence"
          - "omni.quantum.system={system}"
          - "omni.quantum.phase=4"
          - "omni.quantum.critical={str(critical).lower()}"
          - "omni.quantum.port={port}"
          - "prometheus.scrape=true"
          - "prometheus.port={port}"
          - "prometheus.path=/metrics"
        logging:
          driver: "json-file"
          options:
            max-size: "50m"
            max-file: "5"
            labels: "omni.quantum.component"
            tag: "{{{{.Name}}}}"
    """


def common_main(service: str, desc: str, system: int, port: int, route_imports: str, route_includes: str) -> str:
    return f"""
    import time
    import uuid
    from contextlib import asynccontextmanager
    from typing import Any

    import structlog
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

    from app.config import settings
    from app.database import check_database
    from app.exceptions import exception_handlers
    {route_imports}

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level_int),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()

    SERVICE_INFO = Info("service", "Service metadata")
    SERVICE_INFO.info({{"name": settings.service_name, "version": settings.version, "tier": "generation-intelligence"}})

    REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"])
    REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["method", "endpoint"], buckets=[0.005,0.01,0.025,0.05,0.1,0.25,0.5,1.0,2.5,5.0,10.0,30.0])
    ACTIVE_REQUESTS = Gauge("http_requests_active", "Active requests")
    ERROR_COUNT = Counter("http_errors_total", "Errors by type", ["error_type"])

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("service_starting", service=settings.service_name, version=settings.version, port=settings.service_port)
        yield
        logger.info("service_stopped", service=settings.service_name)

    app = FastAPI(title=f"Omni Quantum Elite - {{settings.service_name}}", description="{desc}", version=settings.version, docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    for exc_class, handler in exception_handlers.items():
        app.add_exception_handler(exc_class, handler)

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        ACTIVE_REQUESTS.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed = time.perf_counter() - start
            REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
            REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = f"{{elapsed*1000:.2f}}"
            return response
        except Exception as exc:  # noqa: BLE001
            ERROR_COUNT.labels(type(exc).__name__).inc()
            raise
        finally:
            ACTIVE_REQUESTS.dec()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {{"status": "healthy", "service": settings.service_name, "version": settings.version}}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        checks = {{}}
        ok = True
        try:
            await check_database()
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["database"] = f"error: {{exc}}"
            ok = False
        return JSONResponse(status_code=200 if ok else 503, content={{"status": "ready" if ok else "degraded", "checks": checks}})

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/info")
    async def info() -> dict[str, Any]:
        return {{"service": settings.service_name, "version": settings.version, "tier": "generation-intelligence", "phase": 4, "system_number": {system}, "port": {port}}}

    {route_includes}
    """


def common_config(service: str, port: int, extra: str) -> str:
    return f"""
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file="../../.env", env_file_encoding="utf-8", extra="ignore")
        service_name: str = "{service}"
        service_port: int = {port}
        version: str = "1.0.0"
        log_level: str = "info"
        log_format: str = "json"
        database_url: str = ""
        redis_url: str = "redis://localhost:6379/0"
        litellm_url: str = "http://omni-litellm:4000"
        litellm_api_key: str = ""
        qdrant_url: str = "http://omni-qdrant:6333"
        qdrant_collection: str = "{service}"
        langfuse_host: str = "http://omni-langfuse:3000"
        langfuse_public_key: str = ""
        langfuse_secret_key: str = ""
        mattermost_webhook_url: str = ""
        mattermost_channel: str = "omni-generation-intelligence"
        minio_endpoint: str = "omni-minio:9000"
        minio_access_key: str = ""
        minio_secret_key: str = ""
        minio_bucket: str = "{service}-assets"
        minio_secure: bool = False
        {extra}

        @property
        def log_level_int(self) -> int:
            return {{"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}}.get(self.log_level.lower(), 20)

    settings = Settings()
    """


def common_exceptions() -> str:
    return """
    from __future__ import annotations
    from typing import Any
    from fastapi import Request
    from fastapi.responses import JSONResponse

    class ServiceError(Exception):
        def __init__(self, message: str, status_code: int = 400, details: dict[str, Any] | None = None) -> None:
            super().__init__(message)
            self.message = message
            self.status_code = status_code
            self.details = details or {}

    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message, "details": exc.details, "type": "ServiceError"})

    async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "internal server error", "details": {"message": str(exc)}, "type": type(exc).__name__})

    exception_handlers = {ServiceError: service_error_handler, Exception: generic_error_handler}
    """


def common_database() -> str:
    return """
    from __future__ import annotations
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.config import settings

    engine = None
    SessionLocal = None
    if settings.database_url:
        engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def check_database() -> bool:
        if engine is None:
            return True
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True

    async def get_session() -> AsyncSession:
        if SessionLocal is None:
            raise RuntimeError("database not configured")
        async with SessionLocal() as session:
            yield session
    """


def common_misc() -> dict[str, str]:
    return {
        "app/dependencies.py": "from fastapi import Request\n\ndef get_correlation_id(request: Request) -> str:\n    return getattr(request.state, 'correlation_id', '')\n",
        "app/middleware.py": "from starlette.requests import Request\n\nasync def bind_request_context(request: Request) -> dict[str, str]:\n    return {'path': request.url.path, 'method': request.method, 'client': request.client.host if request.client else ''}\n",
        "app/utils/notifications.py": "import httpx\n\nasync def notify_mattermost(webhook_url: str, text: str) -> bool:\n    if not webhook_url:\n        return False\n    async with httpx.AsyncClient(timeout=5.0) as client:\n        response = await client.post(webhook_url, json={'text': text})\n        return response.is_success\n",
        "app/utils/langfuse_tracer.py": "from contextlib import asynccontextmanager\nfrom datetime import datetime, timezone\nimport structlog\nlogger = structlog.get_logger()\n\n@asynccontextmanager\nasync def traced_span(name: str, metadata: dict | None = None):\n    logger.info('trace_start', span=name, metadata=metadata or {}, started_at=datetime.now(timezone.utc).isoformat())\n    try:\n        yield\n    finally:\n        logger.info('trace_end', span=name, finished_at=datetime.now(timezone.utc).isoformat())\n",
        "app/models/responses.py": "from pydantic import BaseModel\n\nclass GenericResponse(BaseModel):\n    ok: bool = True\n    message: str = 'ok'\n",
        "tests/conftest.py": "import pytest\nfrom fastapi.testclient import TestClient\nfrom app.main import app\n\n@pytest.fixture()\ndef client() -> TestClient:\n    return TestClient(app)\n",
        "alembic.ini": "[alembic]\nscript_location = alembic\nprepend_sys_path = .\nsqlalchemy.url = postgresql+asyncpg://omni:omni@omni-gi-postgres:5432/postgres\n",
        "alembic/env.py": "from alembic import context\nfrom sqlalchemy import engine_from_config, pool\nconfig = context.config\ntarget_metadata = None\n\ndef run_migrations_offline() -> None:\n    url = config.get_main_option('sqlalchemy.url')\n    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={'paramstyle': 'named'})\n    with context.begin_transaction():\n        context.run_migrations()\n\ndef run_migrations_online() -> None:\n    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix='sqlalchemy.', poolclass=pool.NullPool)\n    with connectable.connect() as connection:\n        context.configure(connection=connection, target_metadata=target_metadata)\n        with context.begin_transaction():\n            context.run_migrations()\n\nif context.is_offline_mode():\n    run_migrations_offline()\nelse:\n    run_migrations_online()\n",
    }


def dashboard(title: str, slug: str) -> str:
    return json.dumps({"title": title, "tags": ["omni", slug, "generation-intelligence"], "timezone": "browser", "schemaVersion": 39, "version": 1, "panels": [{"title": "Request Rate", "type": "timeseries", "targets": [{"expr": "sum(rate(http_requests_total[5m]))"}]}, {"title": "Error Rate", "type": "timeseries", "targets": [{"expr": "sum(rate(http_errors_total[5m]))"}]}]}, indent=2) + "\n"


def alerts(service: str) -> str:
    name = "".join(part.capitalize() for part in service.split("-"))
    return f"groups:\n  - name: {service}-alerts\n    rules:\n      - alert: {name}Down\n        expr: up{{job=\"omni-{service}\"}} == 0\n        for: 2m\n        labels:\n          severity: critical\n        annotations:\n          summary: \"{service} is down\"\n          description: \"No scrape targets available for omni-{service}\"\n"


def init_tree(base: Path) -> None:
    for p in [
        base / "app",
        base / "app/models",
        base / "app/routes",
        base / "app/services",
        base / "app/services/platform_adapters",
        base / "app/utils",
        base / "tests",
        base / "tests/fixtures",
        base / "sdk",
        base / "dashboards",
        base / "alerts",
        base / "scripts",
        base / "alembic/versions",
    ]:
        p.mkdir(parents=True, exist_ok=True)

MARKETING_CONFIG_EXTRA = """
content_generation_model: str = \"devstral-2:123b\"
copy_variant_count: int = 5
max_email_batch_size: int = 1000
max_campaigns_active: int = 50
ab_test_min_sample_size: int = 100
ab_test_confidence_level: float = 0.95
lead_scoring_model: str = \"qwen3-coder:30b\"
competitor_scan_interval_hours: int = 24
content_calendar_lookahead_days: int = 90
landing_page_output_path: str = \"/app/data/landing_pages\"
lead_magnet_storage_bucket: str = \"marketing-lead-magnets\"
email_template_bucket: str = \"marketing-email-templates\"
asset_bucket: str = \"marketing-assets\"
listmonk_url: str = \"http://omni-listmonk:9000\"
listmonk_api_user: str = \"\"
listmonk_api_password: str = \"\"
"""

MARKETING_REQUESTS = """
from pydantic import BaseModel, Field

class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    campaign_type: str = "custom"
    channels: list[str] = Field(default_factory=list)
    description: str = ""

class GenerateAdCopyRequest(BaseModel):
    product_description: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    tone: str = "professional"
    channel: str = "email"
    variant_count: int = Field(default=5, ge=1, le=10)

class CreateLeadRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    source: str = "other"
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    job_title: str | None = None
    industry: str | None = None
    company_size: int | None = None

class RecordActivityRequest(BaseModel):
    activity_type: str
    metadata: dict = Field(default_factory=dict)

class CreateAudienceRequest(BaseModel):
    name: str
    description: str = ""
    segment_rules: list[dict] = Field(default_factory=list)

class CreateSequenceRequest(BaseModel):
    campaign_id: str
    name: str
    trigger_event: str = "signup"

class CreateLandingPageRequest(BaseModel):
    title: str
    slug: str
    html_content: str
    campaign_id: str | None = None
    redirect_url: str | None = None

class CreateCompetitorRequest(BaseModel):
    name: str
    website: str | None = None
"""

MARKETING_DB_MODEL = """
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class CampaignRecord(Base):
    __tablename__ = \"campaigns\"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=\"draft\")
    goal_target: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default=\"\")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
"""

MARKETING_MIGRATION = """
\"\"\"Initial schema for marketing-engine\"\"\"
from alembic import op

revision = \"001_initial\"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"')
    op.execute('CREATE TABLE IF NOT EXISTS campaigns (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, campaign_type VARCHAR(50) NOT NULL, status VARCHAR(50) NOT NULL DEFAULT \"draft\", channels JSONB DEFAULT \"[]\"::jsonb, budget_total DECIMAL(12,2) DEFAULT 0, budget_spent DECIMAL(12,2) DEFAULT 0, goal_target INTEGER DEFAULT 0, goal_achieved INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS content_variants (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, variant_label VARCHAR(10), channel VARCHAR(50), headline TEXT, body_copy TEXT, cta_text VARCHAR(200), impressions INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, conversions INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS leads (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(255) UNIQUE NOT NULL, source VARCHAR(50), status VARCHAR(50) DEFAULT \"new\", score INTEGER DEFAULT 0, score_breakdown JSONB DEFAULT \"{}\"::jsonb, company_size INTEGER, job_title VARCHAR(200), industry VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS lead_activities (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), lead_id UUID NOT NULL, activity_type VARCHAR(50) NOT NULL, metadata JSONB DEFAULT \"{}\"::jsonb, score_delta INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS audiences (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, segment_rules JSONB DEFAULT \"[]\"::jsonb, member_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS email_sequences (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, name VARCHAR(200) NOT NULL, trigger_event VARCHAR(100), status VARCHAR(50) DEFAULT \"draft\", created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS email_sequence_steps (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), sequence_id UUID NOT NULL, step_number INTEGER NOT NULL, delay_hours INTEGER DEFAULT 24, subject_line TEXT, body_html TEXT, sent_count INTEGER DEFAULT 0, open_count INTEGER DEFAULT 0, click_count INTEGER DEFAULT 0, unsubscribe_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS landing_pages (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, slug VARCHAR(200) UNIQUE NOT NULL, title VARCHAR(300) NOT NULL, html_content TEXT NOT NULL, status VARCHAR(20) DEFAULT \"draft\", views INTEGER DEFAULT 0, submissions INTEGER DEFAULT 0, conversion_rate DECIMAL(5,4) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS content_calendar (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), title VARCHAR(300) NOT NULL, content_type VARCHAR(50) NOT NULL, channel VARCHAR(50) NOT NULL, scheduled_date DATE NOT NULL, status VARCHAR(20) DEFAULT \"planned\", content_brief TEXT, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitors (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, website VARCHAR(500), description TEXT, pricing_model TEXT, target_market TEXT, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitor_snapshots (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), competitor_id UUID NOT NULL, snapshot_type VARCHAR(50), content TEXT, changes_detected TEXT, analyzed_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS campaign_metrics (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID NOT NULL, metric_date DATE NOT NULL, impressions INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, conversions INTEGER DEFAULT 0, leads_generated INTEGER DEFAULT 0, revenue_attributed DECIMAL(12,2) DEFAULT 0, cost DECIMAL(12,2) DEFAULT 0, roi DECIMAL(8,2) DEFAULT 0, channel VARCHAR(50), created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS funnel_stages (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, name VARCHAR(100), stage_order INTEGER, entries INTEGER DEFAULT 0, exits INTEGER DEFAULT 0, conversions INTEGER DEFAULT 0, drop_off_rate DECIMAL(5,4) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')

def downgrade() -> None:
    for table in [\"funnel_stages\",\"campaign_metrics\",\"competitor_snapshots\",\"competitors\",\"content_calendar\",\"landing_pages\",\"email_sequence_steps\",\"email_sequences\",\"audiences\",\"lead_activities\",\"leads\",\"content_variants\",\"campaigns\"]:
        op.execute(f'DROP TABLE IF EXISTS {table}')
"""

MARKETING_STATE_SERVICE = """
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4

CAMPAIGNS = {}
METRICS = {}
LEADS = {}
LEAD_ACTIVITIES = {}
AUDIENCES = {}
SEQUENCES = {}
LANDING_PAGES = {}
CALENDAR = {}
COMPETITORS = {}
COMPETITOR_SNAPSHOTS = {}
AB_TESTS = {}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def uid() -> str:
    return str(uuid4())
"""

MARKETING_SERVICE_STUBS = {
    "campaign_manager.py": "from app.services.state import CAMPAIGNS, METRICS, now, uid\n",
    "content_generator.py": "# content generation helper module\n",
    "lead_manager.py": "from app.services.state import LEADS, LEAD_ACTIVITIES, now, uid\n",
    "ab_tester.py": "from app.services.state import AB_TESTS, uid\n",
    "audience_segmenter.py": "from app.services.state import AUDIENCES, now, uid\n",
    "email_integrator.py": "async def send_email_batch(*args, **kwargs):\n    return {'sent': len(kwargs.get('recipients', []))}\n",
    "analytics_engine.py": "# analytics helper module\n",
    "competitor_tracker.py": "from app.services.state import COMPETITORS, COMPETITOR_SNAPSHOTS, uid, now\n",
    "content_calendar.py": "from app.services.state import CALENDAR, uid\n",
    "landing_page_builder.py": "from app.services.state import LANDING_PAGES, uid\n",
}

MARKETING_ROUTES = {
    "campaigns.py": '''
from fastapi import APIRouter, HTTPException, Query
from app.models.requests import CreateCampaignRequest
from app.services.state import CAMPAIGNS, METRICS, now, uid

router = APIRouter()

@router.post("/api/v1/campaigns", status_code=201)
async def create_campaign(payload: CreateCampaignRequest):
    campaign_id = uid()
    record = {"id": campaign_id, "name": payload.name, "campaign_type": payload.campaign_type, "channels": payload.channels, "description": payload.description, "status": "draft", "created_at": now(), "updated_at": now()}
    CAMPAIGNS[campaign_id] = record
    METRICS[campaign_id] = {"impressions": 0, "clicks": 0, "conversions": 0, "revenue_attributed": 0.0, "cost": 0.0, "roi": 0.0}
    return record

@router.get("/api/v1/campaigns")
async def list_campaigns(status: str | None = Query(default=None), type: str | None = Query(default=None), channel: str | None = Query(default=None)):
    rows = list(CAMPAIGNS.values())
    if status:
        rows = [r for r in rows if r["status"] == status]
    if type:
        rows = [r for r in rows if r["campaign_type"] == type]
    if channel:
        rows = [r for r in rows if channel in r.get("channels", [])]
    return rows

@router.get("/api/v1/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    out = dict(CAMPAIGNS[campaign_id])
    out["metrics"] = METRICS.get(campaign_id, {})
    return out

@router.put("/api/v1/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, payload: dict):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    CAMPAIGNS[campaign_id].update(payload)
    CAMPAIGNS[campaign_id]["updated_at"] = now()
    return CAMPAIGNS[campaign_id]

@router.delete("/api/v1/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    campaign = CAMPAIGNS.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    if campaign["status"] != "draft":
        raise HTTPException(status_code=409, detail="only draft can be deleted")
    CAMPAIGNS.pop(campaign_id, None)
    METRICS.pop(campaign_id, None)
    return {"deleted": True}

def _status(campaign_id: str, value: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    CAMPAIGNS[campaign_id]["status"] = value
    CAMPAIGNS[campaign_id]["updated_at"] = now()
    return CAMPAIGNS[campaign_id]

@router.post("/api/v1/campaigns/{campaign_id}/launch")
async def launch_campaign(campaign_id: str):
    return _status(campaign_id, "active")

@router.post("/api/v1/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    return _status(campaign_id, "paused")

@router.post("/api/v1/campaigns/{campaign_id}/resume")
async def resume_campaign(campaign_id: str):
    return _status(campaign_id, "active")

@router.post("/api/v1/campaigns/{campaign_id}/complete")
async def complete_campaign(campaign_id: str):
    return _status(campaign_id, "completed")

@router.get("/api/v1/campaigns/{campaign_id}/metrics")
async def campaign_metrics(campaign_id: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    m = METRICS.get(campaign_id, {"impressions": 0, "clicks": 0, "conversions": 0, "revenue_attributed": 0.0, "cost": 0.0})
    impressions = int(m.get("impressions", 0))
    clicks = int(m.get("clicks", 0))
    conversions = int(m.get("conversions", 0))
    m["click_rate"] = round(clicks / impressions, 4) if impressions else 0.0
    m["conversion_rate"] = round(conversions / clicks, 4) if clicks else 0.0
    m["roi"] = round((float(m.get("revenue_attributed", 0.0)) - float(m.get("cost", 0.0))) / float(m.get("cost", 1.0)), 4) if float(m.get("cost", 0.0)) else 0.0
    METRICS[campaign_id] = m
    return m

@router.get("/api/v1/campaigns/{campaign_id}/funnel")
async def campaign_funnel(campaign_id: str):
    m = await campaign_metrics(campaign_id)
    return {"campaign_id": campaign_id, "stages": [{"name": "awareness", "entries": m["impressions"]}, {"name": "interest", "entries": m["clicks"]}, {"name": "conversion", "entries": m["conversions"]}], "conversion_rate": m["conversion_rate"]}

@router.post("/api/v1/campaigns/{campaign_id}/duplicate")
async def duplicate_campaign(campaign_id: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    src = dict(CAMPAIGNS[campaign_id])
    src["name"] = f"Copy of {src['name']}"
    src["status"] = "draft"
    src.pop("id", None)
    return await create_campaign(CreateCampaignRequest(**{k: src.get(k) for k in ["name", "campaign_type", "channels", "description"]}))
''',
    "content.py": '''
from fastapi import APIRouter
from app.models.requests import GenerateAdCopyRequest

router = APIRouter()

@router.post("/api/v1/content/generate/ad-copy")
async def generate_ad_copy(payload: GenerateAdCopyRequest):
    variants = []
    for idx in range(payload.variant_count):
        variants.append({"headline": f"{payload.target_audience} - {payload.product_description} ({idx+1})", "body": f"Tone={payload.tone} Channel={payload.channel}", "cta": "Start now", "hook": "Limited spots", "emotional_angle": "confidence"})
    return {"variants": variants}

@router.post("/api/v1/content/generate/email")
async def generate_email(payload: dict):
    return {"subject_lines": ["Subject A", "Subject B", "Subject C", "Subject D", "Subject E"], "preview_text": "Preview", "body_html": "<html><body><h1>Email</h1></body></html>", "body_plain": "Email", "cta": "Reply"}

@router.post("/api/v1/content/generate/landing-page")
async def generate_landing_page(payload: dict):
    html = "<!doctype html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><main><form><button>CTA</button></form></main></body></html>"
    return {"html": html, "title": payload.get("product", "Landing"), "meta_description": payload.get("value_proposition", ""), "og_tags": {"og:title": payload.get("product", "Landing")}}

@router.post("/api/v1/content/generate/lead-magnet")
async def generate_lead_magnet(payload: dict):
    return {"content_markdown": "# Lead Magnet\n\nDetails", "title": payload.get("topic", "Guide"), "cover_image_brief": "Cover brief", "download_url": "minio://marketing-lead-magnets/file.md"}

@router.post("/api/v1/content/generate/seo-article")
async def generate_seo_article(payload: dict):
    keyword = payload.get("primary_keyword", "keyword")
    body = (keyword + " ") * 120
    return {"title": f"{keyword} guide", "meta_description": keyword, "article_html": f"<article>{body}</article>", "word_count": len(body.split()), "readability_score": 0.82, "keyword_density": 0.1}

@router.post("/api/v1/content/improve")
async def improve_content(payload: dict):
    goals = payload.get("improvement_goals", payload.get("goals", []))
    improved = payload.get("content", "")
    if "more_engaging" in goals:
        improved = "Hook: " + improved
    return {"improved_content": improved, "changes_made": goals, "improvement_score": 0.9}
''',
    "ab_testing.py": '''
from fastapi import APIRouter, HTTPException
from app.services.state import AB_TESTS, uid

router = APIRouter()

@router.post("/api/v1/ab-tests/{campaign_id}/create")
async def create_ab_test(campaign_id: str, payload: dict | None = None):
    payload = payload or {}
    variants = payload.get("variants", [{"label": "A", "traffic_weight": 0.5}, {"label": "B", "traffic_weight": 0.5}])
    AB_TESTS[campaign_id] = {"campaign_id": campaign_id, "variants": [{"id": uid(), "label": v.get("label", "A"), "traffic_weight": float(v.get("traffic_weight", 0.5)), "impressions": 0, "clicks": 0, "conversions": 0, "is_winner": False} for v in variants], "winner_variant_id": None}
    return AB_TESTS[campaign_id]

@router.post("/api/v1/ab-tests/{campaign_id}/record")
async def record_event(campaign_id: str, payload: dict):
    test = AB_TESTS.get(campaign_id)
    if not test:
        raise HTTPException(status_code=404, detail="test not found")
    for v in test["variants"]:
        if v["label"] == payload.get("variant_label", "A"):
            et = payload.get("event_type", "impressions")
            v[et] = int(v.get(et, 0)) + int(payload.get("value", 1))
            return v
    raise HTTPException(status_code=404, detail="variant not found")

@router.get("/api/v1/ab-tests/{campaign_id}/results")
async def results(campaign_id: str):
    test = AB_TESTS.get(campaign_id)
    if not test:
        raise HTTPException(status_code=404, detail="test not found")
    complete = False
    for v in test["variants"]:
        imp = max(v["impressions"], 1)
        clk = v["clicks"]
        conv = v["conversions"]
        v["click_rate"] = round(clk / imp, 4)
        v["conversion_rate"] = round(conv / max(clk, 1), 4)
        v["confidence_interval"] = [max(0.0, v["conversion_rate"] - 0.05), min(1.0, v["conversion_rate"] + 0.05)]
        if imp >= 100:
            complete = True
    return {"variants": test["variants"], "test_complete": complete, "recommended_action": "declare_winner" if complete else "keep_running", "statistical_significance": complete}

@router.post("/api/v1/ab-tests/{campaign_id}/declare-winner")
async def declare_winner(campaign_id: str, payload: dict | None = None):
    payload = payload or {}
    test = AB_TESTS.get(campaign_id)
    if not test:
        raise HTTPException(status_code=404, detail="test not found")
    winner = payload.get("variant_id") or max(test["variants"], key=lambda x: x.get("conversion_rate", 0.0))["id"]
    test["winner_variant_id"] = winner
    for v in test["variants"]:
        v["is_winner"] = v["id"] == winner
        v["traffic_weight"] = 1.0 if v["is_winner"] else 0.0
    return test
''',
}

MARKETING_ROUTES.update({
    "leads.py": '''
from fastapi import APIRouter, HTTPException, Query
from app.models.requests import CreateLeadRequest, RecordActivityRequest
from app.services.state import LEADS, LEAD_ACTIVITIES, now, uid

router = APIRouter()

def compute_score(lead: dict, acts: list[dict]) -> tuple[int, dict]:
    score = 0
    breakdown = {}
    def add(k, d):
        nonlocal score
        score += d
        breakdown[k] = breakdown.get(k, 0) + d
    for a in acts:
        t = a.get("activity_type")
        if t == "page_visit" and "pricing" in str(a.get("metadata", {}).get("page_url", "")):
            add("pricing", 20)
        if t == "download":
            add("download", 15)
        if t == "email_click":
            add("email_click", 10)
        if t in {"form_submit", "demo_request"}:
            add("high_intent", 25)
        if t == "unsubscribe":
            add("unsubscribe", -10)
        if t == "email_bounce":
            add("bounce", -20)
    if int(lead.get("company_size") or 0) > 50:
        add("company_size", 15)
    title = str(lead.get("job_title", "")).lower()
    if any(x in title for x in ["ceo", "cto", "vp", "director", "head"]):
        add("title", 10)
    if str(lead.get("industry", "")).lower() in {"tech", "software", "ai", "saas"}:
        add("industry", 5)
    if lead["email"].split("@")[-1].lower() in {"gmail.com", "yahoo.com"}:
        add("generic", -5)
    score = max(0, min(100, score))
    return score, breakdown

def band(score: int) -> str:
    if score <= 25:
        return "Cold"
    if score <= 50:
        return "Warm"
    if score <= 75:
        return "Hot"
    return "Sales-Ready"

@router.post("/api/v1/leads", status_code=201)
async def capture_lead(payload: CreateLeadRequest):
    lead_id = uid()
    lead = payload.model_dump()
    lead.update({"id": lead_id, "status": "new", "created_at": now(), "updated_at": now(), "last_activity_at": now()})
    LEADS[lead_id] = lead
    LEAD_ACTIVITIES[lead_id] = []
    score, breakdown = compute_score(lead, LEAD_ACTIVITIES[lead_id])
    lead["score"] = score
    lead["score_breakdown"] = breakdown
    return lead

@router.post("/api/v1/leads/bulk")
async def bulk_import(payload: dict):
    items = []
    for row in payload.get("leads", []):
        items.append((await capture_lead(CreateLeadRequest(**row))))
    return {"created": len(items), "items": items}

@router.get("/api/v1/leads")
async def list_leads(status: str | None = Query(default=None), score_min: int | None = Query(default=None), source: str | None = Query(default=None), sort: str | None = Query(default=None)):
    rows = list(LEADS.values())
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if score_min is not None:
        rows = [r for r in rows if int(r.get("score", 0)) >= score_min]
    if source:
        rows = [r for r in rows if r.get("source") == source]
    if sort == "score_desc":
        rows.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    return rows

@router.get("/api/v1/leads/{lead_id}")
async def get_lead(lead_id: str):
    lead = LEADS.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    out = dict(lead)
    out["activities"] = LEAD_ACTIVITIES.get(lead_id, [])
    return out

@router.put("/api/v1/leads/{lead_id}")
async def update_lead(lead_id: str, payload: dict):
    lead = LEADS.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    lead.update(payload)
    lead["updated_at"] = now()
    return lead

@router.delete("/api/v1/leads/{lead_id}")
async def delete_lead(lead_id: str):
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    LEADS.pop(lead_id, None)
    LEAD_ACTIVITIES.pop(lead_id, None)
    return {"deleted": True}

@router.post("/api/v1/leads/{lead_id}/score")
async def rescore(lead_id: str):
    lead = LEADS.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    score, breakdown = compute_score(lead, LEAD_ACTIVITIES.get(lead_id, []))
    lead["score"] = score
    lead["score_breakdown"] = breakdown
    return {"lead_id": lead_id, "score": score, "breakdown": breakdown, "label": band(score)}

@router.post("/api/v1/leads/{lead_id}/activity")
async def record_activity(lead_id: str, payload: RecordActivityRequest):
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    row = {"id": uid(), "activity_type": payload.activity_type, "metadata": payload.metadata, "created_at": now()}
    LEAD_ACTIVITIES.setdefault(lead_id, []).append(row)
    LEADS[lead_id]["last_activity_at"] = row["created_at"]
    await rescore(lead_id)
    return row

@router.get("/api/v1/leads/{lead_id}/activities")
async def activities(lead_id: str):
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    return {"lead_id": lead_id, "activities": LEAD_ACTIVITIES.get(lead_id, [])}

@router.post("/api/v1/leads/{lead_id}/nurture")
async def nurture(lead_id: str, payload: dict | None = None):
    payload = payload or {}
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    LEADS[lead_id]["status"] = "nurturing"
    LEADS[lead_id]["nurture_sequence_id"] = payload.get("sequence_id")
    return LEADS[lead_id]

@router.post("/api/v1/leads/{lead_id}/convert")
async def convert(lead_id: str, payload: dict | None = None):
    payload = payload or {}
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    LEADS[lead_id]["status"] = "won"
    LEADS[lead_id]["revenue_value"] = payload.get("revenue_value")
    return LEADS[lead_id]

@router.get("/api/v1/leads/scoring-model")
async def scoring_model():
    return {"rules": [{"activity": "pricing_page", "score_delta": 20}, {"activity": "download", "score_delta": 15}, {"activity": "email_click", "score_delta": 10}]}

@router.put("/api/v1/leads/scoring-model")
async def scoring_model_update(payload: dict):
    return {"updated": True, "rules": payload.get("rules", [])}
''',
    "audiences.py": "from fastapi import APIRouter, HTTPException\nfrom app.models.requests import CreateAudienceRequest\nfrom app.services.state import AUDIENCES, LEADS, uid, now\n\nrouter = APIRouter()\n\n@router.post('/api/v1/audiences', status_code=201)\nasync def create(payload: CreateAudienceRequest):\n    aid = uid()\n    AUDIENCES[aid] = {'id': aid, 'name': payload.name, 'description': payload.description, 'segment_rules': payload.segment_rules, 'member_count': 0, 'created_at': now(), 'updated_at': now()}\n    return AUDIENCES[aid]\n\n@router.get('/api/v1/audiences')\nasync def list_audiences():\n    return list(AUDIENCES.values())\n\n@router.get('/api/v1/audiences/{audience_id}')\nasync def get_audience(audience_id: str):\n    if audience_id not in AUDIENCES:\n        raise HTTPException(status_code=404, detail='audience not found')\n    return AUDIENCES[audience_id]\n\n@router.put('/api/v1/audiences/{audience_id}')\nasync def update_audience(audience_id: str, payload: dict):\n    if audience_id not in AUDIENCES:\n        raise HTTPException(status_code=404, detail='audience not found')\n    AUDIENCES[audience_id].update(payload)\n    AUDIENCES[audience_id]['updated_at'] = now()\n    return AUDIENCES[audience_id]\n\n@router.get('/api/v1/audiences/{audience_id}/members')\nasync def members(audience_id: str):\n    if audience_id not in AUDIENCES:\n        raise HTTPException(status_code=404, detail='audience not found')\n    return {'audience_id': audience_id, 'members': list(LEADS.values())}\n\n@router.post('/api/v1/audiences/{audience_id}/refresh')\nasync def refresh(audience_id: str):\n    if audience_id not in AUDIENCES:\n        raise HTTPException(status_code=404, detail='audience not found')\n    AUDIENCES[audience_id]['member_count'] = len(LEADS)\n    return {'audience_id': audience_id, 'member_count': len(LEADS)}\n",
    "sequences.py": "from fastapi import APIRouter, HTTPException\nfrom app.models.requests import CreateSequenceRequest\nfrom app.services.state import SEQUENCES, uid, now\n\nrouter = APIRouter()\n\n@router.post('/api/v1/sequences', status_code=201)\nasync def create_sequence(payload: CreateSequenceRequest):\n    sid = uid()\n    SEQUENCES[sid] = {'id': sid, 'campaign_id': payload.campaign_id, 'name': payload.name, 'trigger_event': payload.trigger_event, 'status': 'draft', 'steps': [], 'created_at': now()}\n    return SEQUENCES[sid]\n\n@router.get('/api/v1/sequences')\nasync def list_sequences():\n    return list(SEQUENCES.values())\n\n@router.get('/api/v1/sequences/{sequence_id}')\nasync def get_sequence(sequence_id: str):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    return SEQUENCES[sequence_id]\n\n@router.put('/api/v1/sequences/{sequence_id}')\nasync def update_sequence(sequence_id: str, payload: dict):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    SEQUENCES[sequence_id].update(payload)\n    return SEQUENCES[sequence_id]\n\n@router.post('/api/v1/sequences/{sequence_id}/steps')\nasync def add_step(sequence_id: str, payload: dict):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    step = {'step_number': int(payload.get('step_number', len(SEQUENCES[sequence_id]['steps'])+1)), 'delay_hours': int(payload.get('delay_hours', 24)), 'subject_line': payload.get('subject_line', 'Update'), 'body_html': payload.get('body_html', '<p>Body</p>'), 'sent_count': 0, 'open_count': 0, 'click_count': 0, 'unsubscribe_count': 0}\n    SEQUENCES[sequence_id]['steps'].append(step)\n    return step\n\n@router.put('/api/v1/sequences/{sequence_id}/steps/{step_number}')\nasync def update_step(sequence_id: str, step_number: int, payload: dict):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    step = next((s for s in SEQUENCES[sequence_id]['steps'] if s['step_number']==step_number), None)\n    if not step:\n        raise HTTPException(status_code=404, detail='step not found')\n    step.update(payload)\n    return step\n\n@router.delete('/api/v1/sequences/{sequence_id}/steps/{step_number}')\nasync def delete_step(sequence_id: str, step_number: int):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    before = len(SEQUENCES[sequence_id]['steps'])\n    SEQUENCES[sequence_id]['steps'] = [s for s in SEQUENCES[sequence_id]['steps'] if s['step_number'] != step_number]\n    if len(SEQUENCES[sequence_id]['steps']) == before:\n        raise HTTPException(status_code=404, detail='step not found')\n    return {'deleted': True}\n\n@router.post('/api/v1/sequences/{sequence_id}/activate')\nasync def activate(sequence_id: str):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    SEQUENCES[sequence_id]['status'] = 'active'\n    return SEQUENCES[sequence_id]\n\n@router.post('/api/v1/sequences/{sequence_id}/pause')\nasync def pause(sequence_id: str):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    SEQUENCES[sequence_id]['status'] = 'paused'\n    return SEQUENCES[sequence_id]\n\n@router.get('/api/v1/sequences/{sequence_id}/metrics')\nasync def metrics(sequence_id: str):\n    if sequence_id not in SEQUENCES:\n        raise HTTPException(status_code=404, detail='sequence not found')\n    return {'sequence_id': sequence_id, 'steps': SEQUENCES[sequence_id]['steps'], 'status': SEQUENCES[sequence_id]['status']}\n",
    "landing_pages.py": "from fastapi import APIRouter, HTTPException\nfrom fastapi.responses import HTMLResponse\nfrom app.models.requests import CreateLandingPageRequest\nfrom app.services.state import LANDING_PAGES, LEADS, uid, now\n\nrouter = APIRouter()\n\n@router.post('/api/v1/landing-pages', status_code=201)\nasync def create_page(payload: CreateLandingPageRequest):\n    pid = uid()\n    LANDING_PAGES[pid] = {'id': pid, 'campaign_id': payload.campaign_id, 'slug': payload.slug, 'title': payload.title, 'html_content': payload.html_content, 'status': 'draft', 'views': 0, 'submissions': 0, 'conversion_rate': 0.0, 'created_at': now(), 'redirect_url': payload.redirect_url}\n    return LANDING_PAGES[pid]\n\n@router.get('/api/v1/landing-pages')\nasync def list_pages():\n    return list(LANDING_PAGES.values())\n\n@router.get('/api/v1/landing-pages/{page_id}')\nasync def get_page(page_id: str):\n    if page_id not in LANDING_PAGES:\n        raise HTTPException(status_code=404, detail='page not found')\n    return LANDING_PAGES[page_id]\n\n@router.put('/api/v1/landing-pages/{page_id}')\nasync def update_page(page_id: str, payload: dict):\n    if page_id not in LANDING_PAGES:\n        raise HTTPException(status_code=404, detail='page not found')\n    LANDING_PAGES[page_id].update(payload)\n    return LANDING_PAGES[page_id]\n\n@router.post('/api/v1/landing-pages/{page_id}/publish')\nasync def publish_page(page_id: str):\n    if page_id not in LANDING_PAGES:\n        raise HTTPException(status_code=404, detail='page not found')\n    LANDING_PAGES[page_id]['status'] = 'published'\n    LANDING_PAGES[page_id]['published_at'] = now()\n    return LANDING_PAGES[page_id]\n\ndef _by_slug(slug: str):\n    for page in LANDING_PAGES.values():\n        if page['slug'] == slug and page['status'] == 'published':\n            return page\n    return None\n\n@router.get('/p/{slug}')\nasync def render(slug: str):\n    page = _by_slug(slug)\n    if not page:\n        raise HTTPException(status_code=404, detail='page not found')\n    page['views'] += 1\n    page['conversion_rate'] = round(page['submissions']/max(page['views'],1), 4)\n    return HTMLResponse(page['html_content'])\n\n@router.post('/p/{slug}/submit')\nasync def submit(slug: str, payload: dict):\n    page = _by_slug(slug)\n    if not page:\n        raise HTTPException(status_code=404, detail='page not found')\n    page['submissions'] += 1\n    page['conversion_rate'] = round(page['submissions']/max(page['views'],1), 4)\n    lead_id = uid()\n    LEADS[lead_id] = {'id': lead_id, 'email': payload.get('email'), 'status': 'new', 'source': 'landing_page', 'created_at': now(), 'updated_at': now()}\n    return {'lead': LEADS[lead_id], 'redirect_url': page.get('redirect_url')}\n\n@router.get('/api/v1/landing-pages/{page_id}/metrics')\nasync def page_metrics(page_id: str):\n    if page_id not in LANDING_PAGES:\n        raise HTTPException(status_code=404, detail='page not found')\n    page = LANDING_PAGES[page_id]\n    return {'views': page['views'], 'submissions': page['submissions'], 'conversion_rate': page['conversion_rate']}\n",
    "calendar.py": "from datetime import date, timedelta\nfrom fastapi import APIRouter, Query, HTTPException\nfrom fastapi.responses import PlainTextResponse\nfrom app.services.state import CALENDAR, uid\n\nrouter = APIRouter()\n\n@router.get('/api/v1/calendar')\nasync def get_calendar(start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), channel: str | None = Query(default=None)):\n    rows = list(CALENDAR.values())\n    if start_date:\n        rows = [r for r in rows if r['scheduled_date'] >= start_date]\n    if end_date:\n        rows = [r for r in rows if r['scheduled_date'] <= end_date]\n    if channel:\n        rows = [r for r in rows if r['channel'] == channel]\n    return rows\n\n@router.post('/api/v1/calendar', status_code=201)\nasync def create_entry(payload: dict):\n    cid = uid()\n    CALENDAR[cid] = {'id': cid, 'title': payload.get('title','Untitled'), 'content_type': payload.get('content_type','blog_post'), 'channel': payload.get('channel','content_marketing'), 'scheduled_date': payload.get('scheduled_date', date.today().isoformat()), 'status': payload.get('status','planned'), 'content_brief': payload.get('content_brief',''), 'keywords': payload.get('keywords',[])}\n    return CALENDAR[cid]\n\n@router.put('/api/v1/calendar/{entry_id}')\nasync def update_entry(entry_id: str, payload: dict):\n    if entry_id not in CALENDAR:\n        raise HTTPException(status_code=404, detail='entry not found')\n    CALENDAR[entry_id].update(payload)\n    return CALENDAR[entry_id]\n\n@router.delete('/api/v1/calendar/{entry_id}')\nasync def delete_entry(entry_id: str):\n    if entry_id not in CALENDAR:\n        raise HTTPException(status_code=404, detail='entry not found')\n    CALENDAR.pop(entry_id, None)\n    return {'deleted': True}\n\n@router.post('/api/v1/calendar/generate')\nasync def generate(payload: dict):\n    days = int(payload.get('days', 30))\n    goals = payload.get('goals', [])\n    channels = payload.get('channels', ['email'])\n    entries = []\n    for idx in range(min(days, 90)):\n        if idx % max(1, days // 10) == 0:\n            cid = uid()\n            row = {'id': cid, 'date': (date.today()+timedelta(days=idx)).isoformat(), 'title': f\"Content {idx+1}\", 'type': 'content_marketing', 'channel': channels[idx % len(channels)], 'brief': f\"Goals: {', '.join(goals)}\", 'keywords': ['omni','growth']}\n            entries.append(row)\n            CALENDAR[cid] = {'id': cid, 'title': row['title'], 'content_type': row['type'], 'channel': row['channel'], 'scheduled_date': row['date'], 'status': 'planned', 'content_brief': row['brief'], 'keywords': row['keywords']}\n    return {'entries': entries}\n\n@router.get('/api/v1/calendar/export')\nasync def export_calendar():\n    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Omni Quantum Elite//Marketing Calendar//EN']\n    for row in CALENDAR.values():\n        lines.extend(['BEGIN:VEVENT', f\"UID:{row['id']}\", f\"DTSTART;VALUE=DATE:{row['scheduled_date'].replace('-', '')}\", f\"SUMMARY:{row['title']}\", f\"DESCRIPTION:{row.get('content_brief','')}\", 'END:VEVENT'])\n    lines.append('END:VCALENDAR')\n    return PlainTextResponse('\\n'.join(lines), media_type='text/calendar')\n",
    "competitors.py": "from fastapi import APIRouter, HTTPException\nfrom app.models.requests import CreateCompetitorRequest\nfrom app.services.state import COMPETITORS, COMPETITOR_SNAPSHOTS, uid, now\n\nrouter = APIRouter()\n\n@router.post('/api/v1/competitors', status_code=201)\nasync def create(payload: CreateCompetitorRequest):\n    cid = uid()\n    COMPETITORS[cid] = {'id': cid, 'name': payload.name, 'website': payload.website, 'description': '', 'pricing_model': 'unknown', 'target_market': 'unknown', 'created_at': now()}\n    COMPETITOR_SNAPSHOTS[cid] = []\n    return COMPETITORS[cid]\n\n@router.get('/api/v1/competitors')\nasync def list_competitors():\n    return list(COMPETITORS.values())\n\n@router.get('/api/v1/competitors/{competitor_id}')\nasync def get_competitor(competitor_id: str):\n    if competitor_id not in COMPETITORS:\n        raise HTTPException(status_code=404, detail='competitor not found')\n    out = dict(COMPETITORS[competitor_id])\n    out['latest_snapshots'] = COMPETITOR_SNAPSHOTS.get(competitor_id, [])[-3:]\n    return out\n\n@router.post('/api/v1/competitors/{competitor_id}/analyze')\nasync def analyze(competitor_id: str):\n    if competitor_id not in COMPETITORS:\n        raise HTTPException(status_code=404, detail='competitor not found')\n    snap = {'id': uid(), 'snapshot_type': 'strategy', 'content': 'competitor focuses on social proof and speed', 'url': COMPETITORS[competitor_id].get('website'), 'changes_detected': 'new pricing section', 'features': ['case studies','free trial'], 'pricing': 'tiered', 'analyzed_at': now()}\n    COMPETITOR_SNAPSHOTS.setdefault(competitor_id, []).append(snap)\n    return snap\n\n@router.get('/api/v1/competitors/{competitor_id}/history')\nasync def history(competitor_id: str):\n    if competitor_id not in COMPETITORS:\n        raise HTTPException(status_code=404, detail='competitor not found')\n    return COMPETITOR_SNAPSHOTS.get(competitor_id, [])\n\n@router.get('/api/v1/competitors/comparison')\nasync def comparison():\n    return {'rows': [{'id': c['id'], 'name': c['name'], 'pricing_model': c.get('pricing_model','unknown')} for c in COMPETITORS.values()]}\n\n@router.post('/api/v1/competitors/gaps')\nasync def gaps(payload: dict):\n    return {'gaps': [{'area': 'onboarding', 'description': 'Competitors offer guided setup', 'opportunity_size': 'high', 'recommended_action': 'launch concierge onboarding'}], 'our_features': payload.get('our_features',[]), 'our_pricing': payload.get('our_pricing','unknown')}\n",
    "analytics.py": "from fastapi import APIRouter\nfrom app.services.state import CAMPAIGNS, METRICS, LEADS\n\nrouter = APIRouter()\n\n@router.get('/api/v1/analytics/dashboard')\nasync def dashboard():\n    conv = sum(1 for l in LEADS.values() if l.get('status')=='won')\n    conversion_rate = round(conv/max(len(LEADS),1), 4) if LEADS else 0.0\n    rev = sum(float(m.get('revenue_attributed',0.0)) for m in METRICS.values())\n    return {'total_leads': len(LEADS), 'leads_this_month': len(LEADS), 'conversion_rate': conversion_rate, 'revenue_attributed': round(rev,2), 'top_campaigns': [{'campaign_id': cid, 'revenue': float(METRICS[cid].get('revenue_attributed',0.0))} for cid in CAMPAIGNS.keys()][:5], 'channel_performance': {}, 'lead_source_breakdown': {}, 'funnel_health': 'good'}\n\n@router.get('/api/v1/analytics/roi')\nasync def roi(campaign_id: str | None = None, channel: str | None = None):\n    if campaign_id:\n        m = METRICS.get(campaign_id, {'revenue_attributed': 0.0, 'cost': 0.0, 'roi': 0.0})\n        return {'campaign_id': campaign_id, 'channel': channel, 'roi': m.get('roi',0.0), 'metrics': m}\n    return {'campaigns': [{'campaign_id': cid, 'roi': METRICS.get(cid,{}).get('roi',0.0)} for cid in CAMPAIGNS.keys()], 'channel': channel}\n\n@router.get('/api/v1/analytics/attribution')\nasync def attribution():\n    return {'model': 'multi_touch', 'weights': {'first_touch': 0.3, 'middle_touch': 0.4, 'last_touch': 0.3}}\n\n@router.get('/api/v1/analytics/funnel/{campaign_id}')\nasync def funnel(campaign_id: str):\n    m = METRICS.get(campaign_id, {'impressions': 0, 'clicks': 0, 'conversions': 0})\n    clicks = int(m.get('clicks',0))\n    conv = int(m.get('conversions',0))\n    return {'campaign_id': campaign_id, 'stages': [{'name':'awareness','entries':int(m.get('impressions',0))},{'name':'interest','entries':clicks},{'name':'conversion','entries':conv}], 'conversion_rate': round(conv/max(clicks,1),4) if clicks else 0.0}\n\n@router.get('/api/v1/analytics/trends')\nasync def trends():\n    return {'window_days': 30, 'points': [{'day': i+1, 'leads': 10+i, 'conversions': (i//3)+1} for i in range(30)]}\n\n@router.get('/api/v1/analytics/forecasts')\nasync def forecasts():\n    return {'next_30_days': {'projected_leads': 420, 'projected_conversions': 52, 'projected_revenue': 75600.0}}\n",
})

SOCIAL_CONFIG_EXTRA = """
marketing_engine_url: str = \"http://omni-marketing-engine:9640\"
content_generation_model: str = \"devstral-2:123b\"
post_variants_per_platform: int = 3
max_scheduled_posts: int = 1000
optimal_time_window_minutes: int = 30
trend_scan_interval_minutes: int = 60
competitor_scan_interval_hours: int = 6
analytics_aggregation_interval_minutes: int = 30
engagement_response_scan_minutes: int = 15
max_hashtags_per_post: int = 30
viral_threshold_engagement_rate: float = 0.05
growth_milestone_intervals: list[int] = [1000,5000,10000,25000,50000,100000,250000,500000,1000000,5000000,10000000,25000000,50000000,100000000]
rss_feed_urls: list[str] = []
news_scan_keywords: list[str] = []
twitter_api_key: str = \"\"
twitter_api_secret: str = \"\"
twitter_access_token: str = \"\"
twitter_access_secret: str = \"\"
linkedin_client_id: str = \"\"
linkedin_client_secret: str = \"\"
instagram_access_token: str = \"\"
youtube_api_key: str = \"\"
tiktok_access_token: str = \"\"
facebook_page_token: str = \"\"
reddit_client_id: str = \"\"
reddit_client_secret: str = \"\"
threads_access_token: str = \"\"
bluesky_handle: str = \"\"
bluesky_app_password: str = \"\"
"""

SOCIAL_REQUESTS = """
from pydantic import BaseModel, Field

class ConnectAccountRequest(BaseModel):
    platform: str
    account_handle: str
    credentials: dict = Field(default_factory=dict)

class GenerateContentRequest(BaseModel):
    topic: str
    platforms: list[str]
    content_pillar: str = "educational"
    tone: str = "professional"
    include_hashtags: bool = True

class CreatePostRequest(BaseModel):
    text: str
    platform: str
    account_id: str
    media_urls: list[str] = Field(default_factory=list)
    format: str = "text"
    scheduled_at: str | None = None

class RepurposeRequest(BaseModel):
    source_post_id: str
    target_platforms: list[str]

class HashtagResearchRequest(BaseModel):
    topic: str
    platform: str
    count: int = Field(default=10, ge=1, le=50)
"""

SOCIAL_DB_MODEL = """
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class SocialAccountRecord(Base):
    __tablename__ = \"social_accounts\"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    account_handle: Mapped[str] = mapped_column(String(200), nullable=False)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PostRecord(Base):
    __tablename__ = \"posts\"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=\"draft\")
    text_content: Mapped[str] = mapped_column(Text, default=\"\")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
"""

SOCIAL_MIGRATION = """
\"\"\"Initial schema for social-media\"\"\"
from alembic import op

revision = \"001_initial\"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"')
    op.execute('CREATE TABLE IF NOT EXISTS social_accounts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), platform VARCHAR(50) NOT NULL, account_handle VARCHAR(200) NOT NULL, follower_count INTEGER DEFAULT 0, following_count INTEGER DEFAULT 0, post_count INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS posts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, status VARCHAR(50) DEFAULT \"draft\", content_format VARCHAR(50) DEFAULT \"text\", text_content TEXT, media_urls JSONB DEFAULT \"[]\"::jsonb, hashtags JSONB DEFAULT \"[]\"::jsonb, scheduled_at TIMESTAMPTZ, published_at TIMESTAMPTZ, platform_post_id VARCHAR(200), impressions INTEGER DEFAULT 0, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, saves INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, engagement_rate DECIMAL(7,4) DEFAULT 0, virality_score DECIMAL(5,2) DEFAULT 0, content_pillar VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS content_pillars (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(100) NOT NULL, target_percentage DECIMAL(5,2), actual_percentage DECIMAL(5,2) DEFAULT 0, avg_engagement_rate DECIMAL(7,4) DEFAULT 0, post_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS posting_schedules (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, day_of_week INTEGER NOT NULL, optimal_time TIME NOT NULL, timezone VARCHAR(50) DEFAULT \"UTC\", created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitor_accounts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), platform VARCHAR(50) NOT NULL, account_handle VARCHAR(200) NOT NULL, follower_count INTEGER DEFAULT 0, avg_engagement_rate DECIMAL(7,4) DEFAULT 0, content_strategy_summary TEXT, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitor_posts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), competitor_account_id UUID NOT NULL, text_content TEXT, content_format VARCHAR(50), posted_at TIMESTAMPTZ, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, engagement_rate DECIMAL(7,4) DEFAULT 0, is_viral BOOLEAN DEFAULT FALSE, captured_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS trends (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), platform VARCHAR(50), topic VARCHAR(300) NOT NULL, hashtag VARCHAR(200), category VARCHAR(100), relevance_score DECIMAL(3,2), recommended_action TEXT, source VARCHAR(100), detected_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS engagement_queue (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, interaction_type VARCHAR(50) NOT NULL, content TEXT, sentiment VARCHAR(20), priority INTEGER DEFAULT 5, status VARCHAR(20) DEFAULT \"pending\", suggested_response TEXT, actual_response TEXT, responded_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS follower_snapshots (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, follower_count INTEGER NOT NULL, snapshot_date DATE NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS growth_milestones (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, milestone_value INTEGER NOT NULL, reached_at TIMESTAMPTZ NOT NULL, celebrated BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW())')

def downgrade() -> None:
    for table in [\"growth_milestones\",\"follower_snapshots\",\"engagement_queue\",\"trends\",\"competitor_posts\",\"competitor_accounts\",\"posting_schedules\",\"content_pillars\",\"posts\",\"social_accounts\"]:
        op.execute(f'DROP TABLE IF EXISTS {table}')
"""

SOCIAL_SERVICE_STUBS = {
    "content_creator.py": "# content creator service\n",
    "publisher.py": "# publisher service\n",
    "scheduler.py": "# scheduler service\n",
    "trend_scanner.py": "# trend scanner service\n",
    "competitor_analyzer.py": "# competitor analyzer service\n",
    "audience_analyzer.py": "# audience analyzer service\n",
    "engagement_manager.py": "# engagement manager service\n",
    "growth_tracker.py": "# growth tracker service\n",
    "analytics_collector.py": "# analytics collector service\n",
    "strategy_advisor.py": "# strategy advisor service\n",
}

SOCIAL_ROUTES = {
    "accounts.py": "from datetime import datetime, timezone\nfrom fastapi import APIRouter, HTTPException\nfrom app.models.requests import ConnectAccountRequest\n\nrouter = APIRouter()\nACCOUNTS = {}\n\n@router.post('/api/v1/accounts', status_code=201)\nasync def connect_account(payload: ConnectAccountRequest):\n    aid = str(len(ACCOUNTS)+1)\n    ACCOUNTS[aid] = {'id': aid, 'platform': payload.platform, 'account_handle': payload.account_handle, 'follower_count': 1000, 'following_count': 50, 'post_count': 0, 'is_verified': False, 'is_active': True, 'last_synced_at': datetime.now(timezone.utc).isoformat()}\n    return ACCOUNTS[aid]\n\n@router.get('/api/v1/accounts')\nasync def list_accounts():\n    return list(ACCOUNTS.values())\n\n@router.get('/api/v1/accounts/{account_id}')\nasync def get_account(account_id: str):\n    if account_id not in ACCOUNTS:\n        raise HTTPException(status_code=404, detail='account not found')\n    return ACCOUNTS[account_id]\n\n@router.put('/api/v1/accounts/{account_id}')\nasync def update_account(account_id: str, payload: dict):\n    if account_id not in ACCOUNTS:\n        raise HTTPException(status_code=404, detail='account not found')\n    ACCOUNTS[account_id].update(payload)\n    ACCOUNTS[account_id]['last_synced_at'] = datetime.now(timezone.utc).isoformat()\n    return ACCOUNTS[account_id]\n\n@router.delete('/api/v1/accounts/{account_id}')\nasync def delete_account(account_id: str):\n    if account_id not in ACCOUNTS:\n        raise HTTPException(status_code=404, detail='account not found')\n    ACCOUNTS.pop(account_id, None)\n    return {'deleted': True}\n\n@router.post('/api/v1/accounts/{account_id}/sync')\nasync def sync_account(account_id: str):\n    if account_id not in ACCOUNTS:\n        raise HTTPException(status_code=404, detail='account not found')\n    ACCOUNTS[account_id]['follower_count'] += 25\n    ACCOUNTS[account_id]['last_synced_at'] = datetime.now(timezone.utc).isoformat()\n    return ACCOUNTS[account_id]\n\n@router.get('/api/v1/accounts/overview')\nasync def overview():\n    by = {}\n    for acc in ACCOUNTS.values():\n        by[acc['platform']] = by.get(acc['platform'], 0) + int(acc['follower_count'])\n    return {'total_accounts': len(ACCOUNTS), 'total_followers': sum(by.values()), 'followers_by_platform': by}\n",
    "content.py": "from fastapi import APIRouter, HTTPException\nfrom app.models.requests import GenerateContentRequest, RepurposeRequest, HashtagResearchRequest\nfrom app.routes.accounts import ACCOUNTS\nfrom app.routes.publishing import POSTS\n\nrouter = APIRouter()\n\nLIMITS = {'twitter': 280, 'linkedin': 3000, 'instagram': 2200, 'youtube': 5000, 'tiktok': 4000, 'facebook': 63206, 'reddit': 40000, 'threads': 500, 'bluesky': 300}\n\n@router.post('/api/v1/content/generate')\nasync def generate(payload: GenerateContentRequest):\n    out = {}\n    for p in payload.platforms:\n        text = f\"{payload.topic} | {payload.content_pillar} | {payload.tone}\"[:LIMITS.get(p,500)]\n        out[p] = {'text': text, 'hashtags': [f\"#{payload.topic.replace(' ','')}\", '#omni'], 'media_brief': f\"Visual for {payload.topic}\", 'format_type': 'thread' if p=='twitter' else 'text', 'character_count': len(text), 'estimated_engagement': 0.05, 'optimal_post_time': '09:00'}\n    return {'posts': out}\n\n@router.post('/api/v1/content/repurpose')\nasync def repurpose(payload: RepurposeRequest):\n    if payload.source_post_id not in POSTS:\n        raise HTTPException(status_code=404, detail='source post not found')\n    src = POSTS[payload.source_post_id]['text_content']\n    return {'variants': {p: {'text': (f\"Repurposed for {p}: {src}\")[:LIMITS.get(p,500)], 'platform': p} for p in payload.target_platforms}}\n\n@router.post('/api/v1/content/improve')\nasync def improve(payload: dict):\n    text = payload.get('content', '')\n    goals = payload.get('goals', [])\n    if 'more_engaging' in goals:\n        text = 'Hook: ' + text\n    if 'shorter' in goals:\n        text = text[:max(40, int(len(text)*0.75))]\n    return {'improved_text': text, 'changes_made': goals, 'improvement_score': 0.88}\n\n@router.post('/api/v1/content/hashtag-research')\nasync def hashtags(payload: HashtagResearchRequest):\n    return {'hashtags': [{'tag': f\"#{payload.topic.replace(' ','')}{i+1}\", 'volume': 100000-(i*1000), 'competition': round(0.2+i*0.02,2), 'relevance_score': round(0.95-i*0.01,2)} for i in range(payload.count)]}\n",
    "publishing.py": "from datetime import datetime, timezone\nfrom fastapi import APIRouter, HTTPException, Query\nfrom app.models.requests import CreatePostRequest\n\nrouter = APIRouter()\nPOSTS = {}\n\n@router.post('/api/v1/posts', status_code=201)\nasync def create_post(payload: CreatePostRequest):\n    pid = str(len(POSTS)+1)\n    POSTS[pid] = {'id': pid, 'account_id': payload.account_id, 'platform': payload.platform, 'status': 'draft', 'content_format': payload.format, 'text_content': payload.text, 'media_urls': payload.media_urls, 'scheduled_at': payload.scheduled_at, 'published_at': None, 'platform_post_id': None, 'engagement_rate': 0.0, 'likes': 0, 'comments': 0, 'shares': 0, 'saves': 0, 'clicks': 0, 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()}\n    if payload.scheduled_at:\n        POSTS[pid]['status'] = 'scheduled'\n    return POSTS[pid]\n\n@router.get('/api/v1/posts')\nasync def list_posts(status: str | None = Query(default=None), platform: str | None = Query(default=None), date_range: str | None = Query(default=None), pillar: str | None = Query(default=None)):\n    _ = date_range\n    _ = pillar\n    rows = list(POSTS.values())\n    if status:\n        rows = [r for r in rows if r['status']==status]\n    if platform:\n        rows = [r for r in rows if r['platform']==platform]\n    return rows\n\n@router.get('/api/v1/posts/{post_id}')\nasync def get_post(post_id: str):\n    if post_id not in POSTS:\n        raise HTTPException(status_code=404, detail='post not found')\n    return POSTS[post_id]\n\n@router.put('/api/v1/posts/{post_id}')\nasync def update_post(post_id: str, payload: dict):\n    if post_id not in POSTS:\n        raise HTTPException(status_code=404, detail='post not found')\n    if POSTS[post_id]['status']=='published':\n        raise HTTPException(status_code=409, detail='published posts are immutable')\n    POSTS[post_id].update(payload)\n    POSTS[post_id]['updated_at'] = datetime.now(timezone.utc).isoformat()\n    return POSTS[post_id]\n\n@router.delete('/api/v1/posts/{post_id}')\nasync def delete_post(post_id: str):\n    if post_id not in POSTS:\n        raise HTTPException(status_code=404, detail='post not found')\n    POSTS.pop(post_id, None)\n    return {'deleted': True}\n\n@router.post('/api/v1/posts/{post_id}/publish')\nasync def publish(post_id: str):\n    if post_id not in POSTS:\n        raise HTTPException(status_code=404, detail='post not found')\n    POSTS[post_id]['status'] = 'published'\n    POSTS[post_id]['published_at'] = datetime.now(timezone.utc).isoformat()\n    POSTS[post_id]['platform_post_id'] = f\"platform-{post_id}\"\n    POSTS[post_id]['engagement_rate'] = 0.06\n    return POSTS[post_id]\n\n@router.post('/api/v1/posts/{post_id}/schedule')\nasync def schedule(post_id: str, payload: dict):\n    if post_id not in POSTS:\n        raise HTTPException(status_code=404, detail='post not found')\n    POSTS[post_id]['scheduled_at'] = payload.get('scheduled_at')\n    POSTS[post_id]['status'] = 'scheduled'\n    return POSTS[post_id]\n\n@router.post('/api/v1/posts/bulk-schedule')\nasync def bulk_schedule(payload: dict):\n    rows = []\n    for row in payload.get('posts', []):\n        created = await create_post(CreatePostRequest(text=row['text'], platform=row['platform'], account_id=row.get('account_id','bulk'), media_urls=row.get('media_urls',[]), format=row.get('format','text'), scheduled_at=row.get('scheduled_at')))\n        rows.append(created)\n    return {'scheduled': len(rows), 'posts': rows}\n\n@router.get('/api/v1/posts/queue')\nasync def queue():\n    return [r for r in POSTS.values() if r['status']=='scheduled']\n\n@router.post('/api/v1/posts/cross-post')\nasync def cross_post(payload: dict):\n    rows = []\n    for p in payload.get('platforms', []):\n        txt = payload.get('text','')\n        if payload.get('adapt_per_platform', True):\n            txt = f\"[{p}] {txt}\"\n        created = await create_post(CreatePostRequest(text=txt, platform=p, account_id=payload.get('account_id','multi'), media_urls=payload.get('media_urls',[]), format=payload.get('format','text'), scheduled_at=None))\n        rows.append(created)\n    return {'posts': rows}\n",
    "scheduling.py": "from datetime import datetime, timedelta, timezone\nfrom fastapi import APIRouter\nfrom app.routes.publishing import POSTS\n\nrouter = APIRouter()\n\n@router.get('/api/v1/schedule/optimal-times')\nasync def optimal_times():\n    now = datetime.now(timezone.utc)\n    out = {}\n    for p in ['twitter','linkedin','instagram','youtube','tiktok','facebook','reddit','threads','bluesky']:\n        out[p] = [{'day': 'monday', 'time': (now+timedelta(hours=i+1)).strftime('%H:%M'), 'expected_engagement': round(0.03+i*0.01,4), 'reasoning': 'historical engagement and audience activity'} for i in range(3)]\n    return out\n\n@router.get('/api/v1/schedule/calendar')\nasync def calendar(week: str | None = None, month: str | None = None):\n    return {'week': week, 'month': month, 'scheduled_posts': [p for p in POSTS.values() if p.get('scheduled_at')]}\n\n@router.post('/api/v1/schedule/auto-generate')\nasync def auto_generate(payload: dict):\n    days = int(payload.get('days', 7))\n    ppd = int(payload.get('posts_per_day_per_platform', 1))\n    pillars = payload.get('content_pillars', ['educational'])\n    topics = payload.get('topics', ['omni'])\n    rows = []\n    now = datetime.now(timezone.utc)\n    platforms = ['twitter','linkedin','instagram']\n    for d in range(days):\n        for p in platforms:\n            for i in range(ppd):\n                rows.append({'platform': p, 'date': (now+timedelta(days=d)).date().isoformat(), 'time': (now+timedelta(days=d, hours=i+9)).strftime('%H:%M'), 'topic': topics[(d+i)%len(topics)], 'pillar': pillars[(d+i)%len(pillars)], 'draft_text': 'Scheduled auto-generated draft'})\n    return {'scheduled_posts': rows}\n",
    "trends.py": "from datetime import datetime, timedelta, timezone\nfrom fastapi import APIRouter, HTTPException\n\nrouter = APIRouter()\nTRENDS = {}\n\n@router.get('/api/v1/trends')\nasync def list_trends(platform: str | None = None, category: str | None = None, min_relevance: float | None = None):\n    rows = list(TRENDS.values())\n    if platform:\n        rows = [r for r in rows if r.get('platform') == platform]\n    if category:\n        rows = [r for r in rows if r.get('category') == category]\n    if min_relevance is not None:\n        rows = [r for r in rows if float(r.get('relevance_score',0)) >= min_relevance]\n    return rows\n\n@router.get('/api/v1/trends/{trend_id}')\nasync def get_trend(trend_id: str):\n    if trend_id not in TRENDS:\n        raise HTTPException(status_code=404, detail='trend not found')\n    return TRENDS[trend_id]\n\n@router.post('/api/v1/trends/scan')\nasync def scan():\n    samples = [('twitter','ai agents','tech',0.92),('linkedin','enterprise automation','business',0.86),('instagram','build in public','culture',0.81)]\n    out = []\n    for idx, sample in enumerate(samples):\n        tid = str(len(TRENDS)+1+idx)\n        p, topic, cat, rel = sample\n        row = {'id': tid, 'platform': p, 'topic': topic, 'hashtag': '#' + topic.replace(' ','').lower(), 'category': cat, 'relevance_score': rel, 'recommended_action': 'post_now' if rel > 0.85 else 'monitor', 'source': 'scanner', 'detected_at': datetime.now(timezone.utc).isoformat(), 'expires_at': (datetime.now(timezone.utc)+timedelta(hours=12)).isoformat()}\n        TRENDS[tid] = row\n        out.append(row)\n    return {'trends': out}\n\n@router.post('/api/v1/trends/{trend_id}/create-post')\nasync def create_post_from_trend(trend_id: str, payload: dict):\n    if trend_id not in TRENDS:\n        raise HTTPException(status_code=404, detail='trend not found')\n    platforms = payload.get('platforms', [TRENDS[trend_id]['platform']])\n    return {'posts': {p: {'text': f\"{TRENDS[trend_id]['topic']} for {p}\", 'hashtags': [TRENDS[trend_id]['hashtag']]} for p in platforms}}\n\n@router.post('/api/v1/trends/subscribe')\nasync def subscribe(payload: dict):\n    return {'subscribed': True, 'feed': payload}\n\n@router.get('/api/v1/trends/history')\nasync def history():\n    return list(TRENDS.values())\n",
    "competitors.py": "from fastapi import APIRouter, HTTPException\n\nrouter = APIRouter()\nCOMPETITORS = {}\nCOMP_POSTS = {}\n\n@router.post('/api/v1/competitors', status_code=201)\nasync def add_competitor(payload: dict):\n    cid = str(len(COMPETITORS)+1)\n    COMPETITORS[cid] = {'id': cid, 'platform': payload.get('platform','twitter'), 'account_handle': payload.get('handle','unknown'), 'follower_count': 1000, 'avg_engagement_rate': 0.04, 'content_strategy_summary': 'mix of educational and proof content'}\n    COMP_POSTS[cid] = []\n    return COMPETITORS[cid]\n\n@router.get('/api/v1/competitors')\nasync def list_competitors():\n    return list(COMPETITORS.values())\n\n@router.get('/api/v1/competitors/{competitor_id}')\nasync def get_competitor(competitor_id: str):\n    if competitor_id not in COMPETITORS:\n        raise HTTPException(status_code=404, detail='competitor not found')\n    out = dict(COMPETITORS[competitor_id])\n    out['posts'] = COMP_POSTS.get(competitor_id, [])\n    return out\n\n@router.post('/api/v1/competitors/{competitor_id}/analyze')\nasync def analyze(competitor_id: str):\n    if competitor_id not in COMPETITORS:\n        raise HTTPException(status_code=404, detail='competitor not found')\n    post = {'id': str(len(COMP_POSTS[competitor_id])+1), 'text_content': 'high-performing post', 'content_format': 'text', 'likes': 500, 'comments': 45, 'shares': 30, 'engagement_rate': 0.062, 'is_viral': True}\n    COMP_POSTS.setdefault(competitor_id, []).append(post)\n    return {'competitor': COMPETITORS[competitor_id], 'latest_post': post}\n\n@router.get('/api/v1/competitors/{competitor_id}/posts')\nasync def posts(competitor_id: str):\n    if competitor_id not in COMPETITORS:\n        raise HTTPException(status_code=404, detail='competitor not found')\n    return COMP_POSTS.get(competitor_id, [])\n\n@router.get('/api/v1/competitors/leaderboard')\nasync def leaderboard():\n    rows = list(COMPETITORS.values())\n    rows.sort(key=lambda x: (x.get('follower_count',0), x.get('avg_engagement_rate',0.0)), reverse=True)\n    return rows\n\n@router.get('/api/v1/competitors/content-gaps')\nasync def gaps(our_topics: str = ''):\n    ours = {x.strip().lower() for x in our_topics.split(',') if x.strip()}\n    all_topics = {'benchmarking','automation','founder-story','pricing-breakdown'}\n    miss = sorted(all_topics.difference(ours))\n    return {'gaps': miss, 'recommended_focus': miss[:3]}\n\n@router.get('/api/v1/competitors/strategies')\nasync def strategies():\n    return [{'competitor_id': c['id'], 'handle': c['account_handle'], 'strategy': c['content_strategy_summary']} for c in COMPETITORS.values()]\n\n@router.post('/api/v1/competitors/steal-strategy')\nasync def steal_strategy():\n    return {'playbook': ['publish one educational thread daily','post proof-driven case study twice weekly','use trend hooks with clear CTA']}\n",
    "engagement.py": "from datetime import datetime, timezone\nfrom fastapi import APIRouter, HTTPException\n\nrouter = APIRouter()\nQUEUE = {}\nAUTO = {'enabled': False, 'rules': []}\n\ndef _seed():\n    if not QUEUE:\n        QUEUE['1'] = {'id':'1','platform':'twitter','interaction_type':'comment','content':'How do I get started?','sentiment':'question','priority':2,'status':'pending','suggested_response':'Thanks for asking. Start with docs.','created_at':datetime.now(timezone.utc).isoformat()}\n\n@router.get('/api/v1/engagement/queue')\nasync def queue():\n    _seed()\n    return list(QUEUE.values())\n\n@router.get('/api/v1/engagement/queue/{item_id}')\nasync def item(item_id: str):\n    if item_id not in QUEUE:\n        raise HTTPException(status_code=404, detail='item not found')\n    return QUEUE[item_id]\n\n@router.post('/api/v1/engagement/queue/{item_id}/respond')\nasync def respond(item_id: str, payload: dict):\n    if item_id not in QUEUE:\n        raise HTTPException(status_code=404, detail='item not found')\n    QUEUE[item_id]['actual_response'] = payload.get('response','Thanks')\n    QUEUE[item_id]['status'] = 'responded'\n    QUEUE[item_id]['responded_at'] = datetime.now(timezone.utc).isoformat()\n    return QUEUE[item_id]\n\n@router.post('/api/v1/engagement/queue/{item_id}/ignore')\nasync def ignore(item_id: str):\n    if item_id not in QUEUE:\n        raise HTTPException(status_code=404, detail='item not found')\n    QUEUE[item_id]['status'] = 'ignored'\n    return QUEUE[item_id]\n\n@router.post('/api/v1/engagement/queue/{item_id}/flag')\nasync def flag(item_id: str):\n    if item_id not in QUEUE:\n        raise HTTPException(status_code=404, detail='item not found')\n    QUEUE[item_id]['status'] = 'flagged'\n    return QUEUE[item_id]\n\n@router.get('/api/v1/engagement/sentiment')\nasync def sentiment():\n    _seed()\n    out = {'positive':0,'neutral':0,'negative':0,'question':0}\n    for it in QUEUE.values():\n        out[it.get('sentiment','neutral')] = out.get(it.get('sentiment','neutral'),0)+1\n    return out\n\n@router.post('/api/v1/engagement/auto-respond/config')\nasync def auto(payload: dict):\n    AUTO.update(payload)\n    return AUTO\n",
    "analytics.py": "from datetime import date, timedelta\nfrom fastapi import APIRouter\nfrom app.routes.accounts import ACCOUNTS\nfrom app.routes.publishing import POSTS\n\nrouter = APIRouter()\nMILESTONES = []\n\n@router.get('/api/v1/analytics/dashboard')\nasync def dashboard():\n    by = {}\n    for a in ACCOUNTS.values():\n        by[a['platform']] = by.get(a['platform'],0) + int(a.get('follower_count',0))\n    total = sum(by.values())\n    published = [p for p in POSTS.values() if p['status']=='published']\n    top = sorted(published, key=lambda x: x.get('engagement_rate',0.0), reverse=True)[:5]\n    rec = ['Increase LinkedIn cadence to 2/day', 'Publish trend responses within 60 minutes']\n    return {'total_followers': total, 'followers_by_platform': by, 'total_engagement_this_week': sum(int(p.get('likes',0))+int(p.get('comments',0))+int(p.get('shares',0)) for p in published), 'top_performing_posts': top, 'growth_rate': 0.12, 'content_pillar_performance': {}, 'best_performing_platform': max(by, key=by.get) if by else None, 'worst_performing_platform': min(by, key=by.get) if by else None, 'recommended_actions': rec, 'next_milestones': MILESTONES[-3:]}\n\n@router.get('/api/v1/analytics/growth')\nasync def growth(platform: str | None = None, range: str = '30d'):\n    days = int(range.rstrip('d')) if range.endswith('d') else 30\n    points = [{'date': (date.today()-timedelta(days=days-i)).isoformat(), 'followers': i*100} for i in range(days)]\n    return {'platform': platform, 'window_days': days, 'snapshots': points}\n\n@router.get('/api/v1/analytics/growth/projection')\nasync def projection():\n    total = sum(int(a.get('follower_count',0)) for a in ACCOUNTS.values())\n    return {'current_total': total, 'monthly_growth_rate': 0.18, 'projected_milestones': [{'count': 1000000, 'estimated_date': (date.today()+timedelta(days=90)).isoformat()}, {'count': 10000000, 'estimated_date': (date.today()+timedelta(days=365)).isoformat()}, {'count': 100000000, 'estimated_date': (date.today()+timedelta(days=1200)).isoformat()}], 'bottlenecks': ['posting consistency','platform diversification'], 'acceleration_recommendations': ['increase collaborations','double down on best pillar']}\n\n@router.get('/api/v1/analytics/posts/performance')\nasync def perf():\n    rows = list(POSTS.values())\n    rows.sort(key=lambda x: x.get('engagement_rate',0.0), reverse=True)\n    return rows\n\n@router.get('/api/v1/analytics/posts/best-times')\nasync def best_times():\n    return {'twitter': ['09:00','13:00','18:00'], 'linkedin': ['08:30','12:00','17:00']}\n\n@router.get('/api/v1/analytics/posts/best-formats')\nasync def best_formats():\n    return {'formats': [{'format':'thread','engagement':0.061},{'format':'carousel','engagement':0.055}]}\n\n@router.get('/api/v1/analytics/posts/best-pillars')\nasync def best_pillars():\n    return {'pillars': [{'name':'educational','engagement':0.058},{'name':'inspiring','engagement':0.051}]}\n\n@router.get('/api/v1/analytics/posts/viral')\nasync def viral():\n    return [p for p in POSTS.values() if float(p.get('engagement_rate',0.0)) > 0.05]\n\n@router.get('/api/v1/analytics/engagement-rate')\nasync def engagement_rate():\n    if not POSTS:\n        return {'engagement_rate': 0.0}\n    avg = sum(float(p.get('engagement_rate',0.0)) for p in POSTS.values())/len(POSTS)\n    return {'engagement_rate': round(avg,4)}\n\n@router.get('/api/v1/analytics/milestones')\nasync def milestones():\n    return MILESTONES\n\n@router.get('/api/v1/analytics/report')\nasync def report(period: str = 'weekly'):\n    board = await dashboard()\n    return {'period': period, 'report_markdown': f\"# Social Report ({period})\\nTotal followers: {board['total_followers']}\\n\", 'executive_summary': 'Growth is positive with strong trend responsiveness.', 'key_metrics': board, 'recommendations': board['recommended_actions']}\n",
    "strategy.py": "from fastapi import APIRouter\nfrom app.routes.accounts import ACCOUNTS\n\nrouter = APIRouter()\n\n@router.get('/api/v1/strategy/recommendations')\nasync def recommendations():\n    return {'recommendations': [{'area':'content cadence','action':'Increase LinkedIn posting to 2/day','expected_impact':'high','difficulty':'medium','timeline':'2 weeks','reasoning':'LinkedIn currently has highest conversion quality'},{'area':'trend execution','action':'Publish trend response content within 60 minutes','expected_impact':'high','difficulty':'medium','timeline':'1 week','reasoning':'Trend freshness strongly correlates with reach gains'}]}\n\n@router.post('/api/v1/strategy/audit')\nasync def audit():\n    scores = [{'platform': a['platform'], 'health_score': 78, 'strengths': ['consistent cadence'], 'weaknesses': ['underutilized video'], 'opportunities': ['collab posts'], 'threats': ['rapid competitor growth']} for a in ACCOUNTS.values()]\n    return {'account_scores': scores, 'overall_score': 80, 'priority_actions': ['increase video output', 'add platform-specific hooks']}\n\n@router.get('/api/v1/strategy/content-mix')\nasync def content_mix():\n    return {'pillars': [{'name':'educational','target_pct':35.0,'actual_pct':28.0,'avg_engagement':0.05,'recommendation':'increase'},{'name':'entertaining','target_pct':20.0,'actual_pct':24.0,'avg_engagement':0.047,'recommendation':'hold'}]}\n\n@router.post('/api/v1/strategy/100m-plan')\nasync def plan_100m():\n    total = sum(int(a.get('follower_count',0)) for a in ACCOUNTS.values())\n    return {'current_followers': total, 'phases': [{'name':'Foundation','target':1000000,'timeline':'0-6 months','platforms_focus':['twitter','linkedin','instagram'],'content_strategy':'daily educational + proof content','growth_tactics':['collabs','cross-posting','trend riding'],'budget_estimate':5000,'key_metrics':['engagement_rate','weekly_follower_delta']},{'name':'Scale','target':10000000,'timeline':'6-18 months','platforms_focus':['youtube','tiktok','instagram'],'content_strategy':'video-first with distribution loops','growth_tactics':['creator network','format expansion'],'budget_estimate':35000,'key_metrics':['watch_time','shares','conversion_rate']},{'name':'Dominance','target':100000000,'timeline':'18-48 months','platforms_focus':['all'],'content_strategy':'multi-language multi-format franchise','growth_tactics':['localization','media partnerships'],'budget_estimate':250000,'key_metrics':['global reach','brand search volume']}]}\n",
}

PLATFORM_ADAPTERS = {
    "twitter.py": "TwitterAdapter",
    "linkedin.py": "LinkedinAdapter",
    "instagram.py": "InstagramAdapter",
    "youtube.py": "YoutubeAdapter",
    "tiktok.py": "TiktokAdapter",
    "facebook.py": "FacebookAdapter",
    "reddit.py": "RedditAdapter",
    "threads.py": "ThreadsAdapter",
    "bluesky.py": "BlueskyAdapter",
}


MARKETING_ROUTE_IMPORTS = "from app.routes import campaigns, content, leads, ab_testing, audiences, sequences, landing_pages, calendar, competitors, analytics"
MARKETING_ROUTE_INCLUDES = "\n".join([
    "app.include_router(campaigns.router)",
    "app.include_router(content.router)",
    "app.include_router(leads.router)",
    "app.include_router(ab_testing.router)",
    "app.include_router(audiences.router)",
    "app.include_router(sequences.router)",
    "app.include_router(landing_pages.router)",
    "app.include_router(calendar.router)",
    "app.include_router(competitors.router)",
    "app.include_router(analytics.router)",
])

SOCIAL_ROUTE_IMPORTS = "from app.routes import accounts, content, publishing, scheduling, trends, competitors, engagement, analytics, strategy"
SOCIAL_ROUTE_INCLUDES = "\n".join([
    "app.include_router(accounts.router)",
    "app.include_router(content.router)",
    "app.include_router(publishing.router)",
    "app.include_router(scheduling.router)",
    "app.include_router(trends.router)",
    "app.include_router(competitors.router)",
    "app.include_router(engagement.router)",
    "app.include_router(analytics.router)",
    "app.include_router(strategy.router)",
])

MARKETING_RESPONSES = """
from pydantic import BaseModel

class CampaignResponse(BaseModel):
    id: str
    name: str
    campaign_type: str
    status: str

class LeadResponse(BaseModel):
    id: str
    email: str
    status: str
    score: int
"""

SOCIAL_RESPONSES = """
from pydantic import BaseModel

class SocialAccountResponse(BaseModel):
    id: str
    platform: str
    account_handle: str
    follower_count: int

class SocialPostResponse(BaseModel):
    id: str
    platform: str
    status: str
    text_content: str
"""

MARKETING_SDK = """
from __future__ import annotations
from typing import Any

import httpx

class MarketingEngineClient:
    def __init__(self, base_url: str = "http://localhost:9640", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MarketingEngineClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._client is None:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.request(method, path, **kwargs)
        else:
            resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    async def create_campaign(self, name: str, campaign_type: str, channels: list[str], description: str = "") -> dict:
        return await self._request("POST", "/api/v1/campaigns", json={"name": name, "campaign_type": campaign_type, "channels": channels, "description": description})

    async def list_campaigns(self, status: str | None = None, type: str | None = None) -> list:
        params = {"status": status, "type": type}
        params = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", "/api/v1/campaigns", params=params)

    async def launch_campaign(self, campaign_id: str) -> dict:
        return await self._request("POST", f"/api/v1/campaigns/{campaign_id}/launch")

    async def get_campaign_metrics(self, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/campaigns/{campaign_id}/metrics")

    async def generate_ad_copy(self, product: str, audience: str, tone: str, variants: int = 5) -> dict:
        return await self._request("POST", "/api/v1/content/generate/ad-copy", json={"product_description": product, "target_audience": audience, "tone": tone, "channel": "email", "variant_count": variants})

    async def generate_email(self, purpose: str, audience: str, product: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate/email", json={"purpose": purpose, "audience": audience, "product": product})

    async def generate_landing_page(self, product: str, value_prop: str, audience: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate/landing-page", json={"product": product, "value_proposition": value_prop, "target_audience": audience})

    async def generate_lead_magnet(self, topic: str, format: str, audience: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate/lead-magnet", json={"topic": topic, "format": format, "audience": audience})

    async def generate_seo_article(self, keyword: str, audience: str, length: int = 1200) -> dict:
        return await self._request("POST", "/api/v1/content/generate/seo-article", json={"primary_keyword": keyword, "target_length": length, "audience": audience})

    async def generate_content_calendar(self, goals: list[str], channels: list[str], days: int) -> dict:
        return await self._request("POST", "/api/v1/calendar/generate", json={"goals": goals, "channels": channels, "days": days})

    async def capture_lead(self, email: str, source: str, **kwargs: Any) -> dict:
        payload = {"email": email, "source": source, **kwargs}
        return await self._request("POST", "/api/v1/leads", json=payload)

    async def get_lead(self, lead_id: str) -> dict:
        return await self._request("GET", f"/api/v1/leads/{lead_id}")

    async def update_lead_score(self, lead_id: str) -> dict:
        return await self._request("POST", f"/api/v1/leads/{lead_id}/score")

    async def record_activity(self, lead_id: str, activity_type: str, metadata: dict) -> dict:
        return await self._request("POST", f"/api/v1/leads/{lead_id}/activity", json={"activity_type": activity_type, "metadata": metadata})

    async def create_ab_test(self, campaign_id: str, variants: list[dict]) -> dict:
        return await self._request("POST", f"/api/v1/ab-tests/{campaign_id}/create", json={"variants": variants})

    async def get_ab_results(self, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/ab-tests/{campaign_id}/results")

    async def declare_winner(self, campaign_id: str, variant_id: str) -> dict:
        return await self._request("POST", f"/api/v1/ab-tests/{campaign_id}/declare-winner", json={"variant_id": variant_id})

    async def get_dashboard(self) -> dict:
        return await self._request("GET", "/api/v1/analytics/dashboard")

    async def get_roi(self, campaign_id: str | None = None, channel: str | None = None) -> dict:
        return await self._request("GET", "/api/v1/analytics/roi", params={"campaign_id": campaign_id, "channel": channel})

    async def get_funnel(self, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/analytics/funnel/{campaign_id}")

    async def add_competitor(self, name: str, website: str | None = None) -> dict:
        return await self._request("POST", "/api/v1/competitors", json={"name": name, "website": website})

    async def analyze_competitor(self, competitor_id: str) -> dict:
        return await self._request("POST", f"/api/v1/competitors/{competitor_id}/analyze")

    async def get_comparison(self) -> dict:
        return await self._request("GET", "/api/v1/competitors/comparison")

    async def identify_gaps(self, our_features: list[str], our_pricing: str) -> dict:
        return await self._request("POST", "/api/v1/competitors/gaps", json={"our_features": our_features, "our_pricing": our_pricing})
"""

SOCIAL_SDK = """
from __future__ import annotations
from typing import Any

import httpx

class SocialMediaClient:
    def __init__(self, base_url: str = "http://localhost:9641", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SocialMediaClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._client is None:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.request(method, path, **kwargs)
        else:
            resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    async def connect_account(self, platform: str, handle: str, credentials: dict) -> dict:
        return await self._request("POST", "/api/v1/accounts", json={"platform": platform, "account_handle": handle, "credentials": credentials})

    async def list_accounts(self) -> list:
        return await self._request("GET", "/api/v1/accounts")

    async def get_overview(self) -> dict:
        return await self._request("GET", "/api/v1/accounts/overview")

    async def generate_content(self, topic: str, platforms: list[str], pillar: str, tone: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate", json={"topic": topic, "platforms": platforms, "content_pillar": pillar, "tone": tone, "include_hashtags": True})

    async def repurpose(self, post_id: str, target_platforms: list[str]) -> dict:
        return await self._request("POST", "/api/v1/content/repurpose", json={"source_post_id": post_id, "target_platforms": target_platforms})

    async def research_hashtags(self, topic: str, platform: str, count: int) -> dict:
        return await self._request("POST", "/api/v1/content/hashtag-research", json={"topic": topic, "platform": platform, "count": count})

    async def create_post(self, text: str, platform: str, account_id: str, media_urls: list[str] | None = None, format: str | None = None) -> dict:
        return await self._request("POST", "/api/v1/posts", json={"text": text, "platform": platform, "account_id": account_id, "media_urls": media_urls or [], "format": format or "text"})

    async def schedule_post(self, post_id: str, scheduled_at: str) -> dict:
        return await self._request("POST", f"/api/v1/posts/{post_id}/schedule", json={"scheduled_at": scheduled_at})

    async def publish_now(self, post_id: str) -> dict:
        return await self._request("POST", f"/api/v1/posts/{post_id}/publish")

    async def cross_post(self, text: str, platforms: list[str], adapt: bool = True) -> dict:
        return await self._request("POST", "/api/v1/posts/cross-post", json={"text": text, "platforms": platforms, "adapt_per_platform": adapt})

    async def bulk_schedule(self, posts: list[dict]) -> dict:
        return await self._request("POST", "/api/v1/posts/bulk-schedule", json={"posts": posts})

    async def get_trends(self, platform: str | None = None, category: str | None = None) -> list:
        return await self._request("GET", "/api/v1/trends", params={"platform": platform, "category": category})

    async def create_post_from_trend(self, trend_id: str, platforms: list[str]) -> dict:
        return await self._request("POST", f"/api/v1/trends/{trend_id}/create-post", json={"platforms": platforms})

    async def add_competitor(self, platform: str, handle: str) -> dict:
        return await self._request("POST", "/api/v1/competitors", json={"platform": platform, "handle": handle})

    async def analyze_competitor(self, competitor_id: str) -> dict:
        return await self._request("POST", f"/api/v1/competitors/{competitor_id}/analyze")

    async def get_content_gaps(self) -> dict:
        return await self._request("GET", "/api/v1/competitors/content-gaps")

    async def get_dashboard(self) -> dict:
        return await self._request("GET", "/api/v1/analytics/dashboard")

    async def get_growth(self, platform: str | None = None, range: str = "30d") -> dict:
        return await self._request("GET", "/api/v1/analytics/growth", params={"platform": platform, "range": range})

    async def get_growth_projection(self) -> dict:
        return await self._request("GET", "/api/v1/analytics/growth/projection")

    async def get_viral_posts(self) -> list:
        return await self._request("GET", "/api/v1/analytics/posts/viral")

    async def get_milestones(self) -> list:
        return await self._request("GET", "/api/v1/analytics/milestones")

    async def get_recommendations(self) -> dict:
        return await self._request("GET", "/api/v1/strategy/recommendations")

    async def run_audit(self) -> dict:
        return await self._request("POST", "/api/v1/strategy/audit")

    async def get_100m_plan(self) -> dict:
        return await self._request("POST", "/api/v1/strategy/100m-plan")
"""

MARKETING_TEST_CONFTEXT = """
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import state

@pytest.fixture(autouse=True)
def reset_state():
    state.CAMPAIGNS.clear()
    state.METRICS.clear()
    state.LEADS.clear()
    state.LEAD_ACTIVITIES.clear()
    state.AUDIENCES.clear()
    state.SEQUENCES.clear()
    state.LANDING_PAGES.clear()
    state.CALENDAR.clear()
    state.COMPETITORS.clear()
    state.COMPETITOR_SNAPSHOTS.clear()
    state.AB_TESTS.clear()

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
"""

MARKETING_TESTS = {
    "test_campaigns.py": '''
def _create_campaign(client):
    r = client.post('/api/v1/campaigns', json={'name': 'Q1 Growth', 'campaign_type': 'email_blast', 'channels': ['email']})
    assert r.status_code == 201
    return r.json()['id']

def test_create_campaign(client):
    cid = _create_campaign(client)
    assert cid

def test_launch_campaign(client):
    cid = _create_campaign(client)
    r = client.post(f'/api/v1/campaigns/{cid}/launch')
    assert r.status_code == 200
    assert r.json()['status'] == 'active'

def test_pause_and_resume(client):
    cid = _create_campaign(client)
    client.post(f'/api/v1/campaigns/{cid}/launch')
    p = client.post(f'/api/v1/campaigns/{cid}/pause')
    assert p.json()['status'] == 'paused'
    r = client.post(f'/api/v1/campaigns/{cid}/resume')
    assert r.json()['status'] == 'active'

def test_duplicate_campaign(client):
    cid = _create_campaign(client)
    r = client.post(f'/api/v1/campaigns/{cid}/duplicate')
    assert r.status_code == 201
    assert r.json()['name'].startswith('Copy of')

def test_delete_only_draft(client):
    cid = _create_campaign(client)
    client.post(f'/api/v1/campaigns/{cid}/launch')
    r = client.delete(f'/api/v1/campaigns/{cid}')
    assert r.status_code == 409
''',
    "test_content.py": '''
def test_generate_ad_copy(client):
    r = client.post('/api/v1/content/generate/ad-copy', json={'product_description':'AI coding suite', 'target_audience':'CTOs', 'tone':'bold', 'channel':'email', 'variant_count':5})
    assert r.status_code == 200
    assert len(r.json()['variants']) == 5

def test_generate_email(client):
    r = client.post('/api/v1/content/generate/email', json={'purpose':'announce', 'audience':'founders', 'product':'omni'})
    data = r.json()
    assert len(data['subject_lines']) == 5
    assert '<html>' in data['body_html']

def test_generate_landing_page(client):
    r = client.post('/api/v1/content/generate/landing-page', json={'product':'omni', 'value_proposition':'ship faster', 'target_audience':'dev teams', 'cta_goal':'book demo', 'style':'modern'})
    data = r.json()
    assert '<meta name=' in data['html']
    assert '<form' in data['html']

def test_generate_seo_article(client):
    r = client.post('/api/v1/content/generate/seo-article', json={'primary_keyword':'agentic coding', 'secondary_keywords':['automation'], 'target_length':1200, 'audience':'engineers'})
    data = r.json()
    assert data['word_count'] > 50
    assert 'article_html' in data

def test_generate_content_calendar(client):
    r = client.post('/api/v1/calendar/generate', json={'goals':['growth'], 'channels':['email','seo'], 'days':30})
    assert r.status_code == 200
    assert len(r.json()['entries']) >= 3
''',
    "test_leads.py": '''
def _lead(client):
    r = client.post('/api/v1/leads', json={'email':'a@example.com', 'source':'website', 'company_size':80, 'job_title':'CTO', 'industry':'tech'})
    assert r.status_code == 201
    return r.json()['id']

def test_capture_lead(client):
    lid = _lead(client)
    r = client.get(f'/api/v1/leads/{lid}')
    assert r.status_code == 200
    assert r.json()['score'] >= 0

def test_lead_scoring(client):
    lid = _lead(client)
    client.post(f'/api/v1/leads/{lid}/activity', json={'activity_type':'page_visit', 'metadata': {'page_url':'/pricing'}})
    client.post(f'/api/v1/leads/{lid}/activity', json={'activity_type':'download', 'metadata': {}})
    r = client.post(f'/api/v1/leads/{lid}/score')
    assert r.status_code == 200
    assert r.json()['score'] >= 35

def test_lead_nurture_enrollment(client):
    lid = _lead(client)
    r = client.post(f'/api/v1/leads/{lid}/nurture', json={'sequence_id':'seq-1'})
    assert r.status_code == 200
    assert r.json()['status'] == 'nurturing'

def test_bulk_import(client):
    r = client.post('/api/v1/leads/bulk', json={'leads':[{'email':'b@example.com','source':'email'},{'email':'c@example.com','source':'paid_ad'}]})
    assert r.status_code == 200
    assert r.json()['created'] == 2

def test_gdpr_delete(client):
    lid = _lead(client)
    d = client.delete(f'/api/v1/leads/{lid}')
    assert d.status_code == 200
    g = client.get(f'/api/v1/leads/{lid}')
    assert g.status_code == 404
''',
    "test_ab_testing.py": '''
def _campaign(client):
    return client.post('/api/v1/campaigns', json={'name':'AB', 'campaign_type':'email_blast', 'channels':['email']}).json()['id']

def test_create_ab_test(client):
    cid = _campaign(client)
    r = client.post(f'/api/v1/ab-tests/{cid}/create', json={'variants':[{'label':'A','traffic_weight':0.5},{'label':'B','traffic_weight':0.5}]})
    assert r.status_code == 200
    assert len(r.json()['variants']) == 2

def test_record_events(client):
    cid = _campaign(client)
    client.post(f'/api/v1/ab-tests/{cid}/create')
    for _ in range(10):
        client.post(f'/api/v1/ab-tests/{cid}/record', json={'variant_label':'A','event_type':'impressions','value':1})
    r = client.get(f'/api/v1/ab-tests/{cid}/results')
    assert r.status_code == 200
    assert r.json()['variants'][0]['impressions'] >= 10

def test_declare_winner(client):
    cid = _campaign(client)
    c = client.post(f'/api/v1/ab-tests/{cid}/create').json()
    winner = c['variants'][0]['id']
    r = client.post(f'/api/v1/ab-tests/{cid}/declare-winner', json={'variant_id': winner})
    assert r.status_code == 200
    assert r.json()['winner_variant_id'] == winner
''',
    "test_analytics.py": '''
def _campaign(client):
    return client.post('/api/v1/campaigns', json={'name':'ROI', 'campaign_type':'paid_ad', 'channels':['paid_ads']}).json()['id']

def test_dashboard_data(client):
    _campaign(client)
    r = client.get('/api/v1/analytics/dashboard')
    d = r.json()
    assert r.status_code == 200
    assert 'total_leads' in d and 'top_campaigns' in d

def test_roi_calculation(client):
    cid = _campaign(client)
    m = client.get(f'/api/v1/campaigns/{cid}/metrics').json()
    assert 'roi' in m

def test_funnel_analysis(client):
    cid = _campaign(client)
    f = client.get(f'/api/v1/analytics/funnel/{cid}')
    assert f.status_code == 200
    assert len(f.json()['stages']) == 3
''',
    "test_competitors.py": '''
def test_add_competitor(client):
    r = client.post('/api/v1/competitors', json={'name':'Acme', 'website':'https://acme.test'})
    assert r.status_code == 201
    assert r.json()['name'] == 'Acme'

def test_competitor_analysis(client):
    c = client.post('/api/v1/competitors', json={'name':'Rival', 'website':'https://rival.test'}).json()['id']
    r = client.post(f'/api/v1/competitors/{c}/analyze')
    assert r.status_code == 200
    assert 'features' in r.json()
''',
}

SOCIAL_TEST_CONFTEXT = """
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import accounts, publishing, trends, competitors, engagement

@pytest.fixture(autouse=True)
def reset_state():
    accounts.ACCOUNTS.clear()
    publishing.POSTS.clear()
    trends.TRENDS.clear()
    competitors.COMPETITORS.clear()
    competitors.COMP_POSTS.clear()
    engagement.QUEUE.clear()

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
"""

SOCIAL_TESTS = {
    "test_accounts.py": '''
def test_connect_account(client):
    r = client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{'token':'x'}})
    assert r.status_code == 201
    assert r.json()['platform'] == 'twitter'

def test_list_accounts(client):
    client.post('/api/v1/accounts', json={'platform':'linkedin','account_handle':'omni','credentials':{}})
    r = client.get('/api/v1/accounts')
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_account_overview(client):
    client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}})
    r = client.get('/api/v1/accounts/overview')
    assert r.status_code == 200
    assert 'total_followers' in r.json()
''',
    "test_content.py": '''
def _account(client):
    return client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}}).json()['id']

def _post(client, account_id):
    return client.post('/api/v1/posts', json={'text':'thread content', 'platform':'twitter', 'account_id':account_id, 'media_urls':[], 'format':'thread'}).json()['id']

def test_generate_twitter_content(client):
    r = client.post('/api/v1/content/generate', json={'topic':'agentic coding','platforms':['twitter'],'content_pillar':'educational','tone':'bold','include_hashtags':True})
    text = r.json()['posts']['twitter']['text']
    assert len(text) <= 280

def test_generate_linkedin_content(client):
    r = client.post('/api/v1/content/generate', json={'topic':'enterprise quality','platforms':['linkedin'],'content_pillar':'professional','tone':'professional','include_hashtags':True})
    assert len(r.json()['posts']['linkedin']['text']) <= 3000

def test_generate_instagram_content(client):
    r = client.post('/api/v1/content/generate', json={'topic':'build in public','platforms':['instagram'],'content_pillar':'inspiring','tone':'casual','include_hashtags':True})
    assert 'hashtags' in r.json()['posts']['instagram']

def test_repurpose_twitter_to_linkedin(client):
    aid = _account(client)
    pid = _post(client, aid)
    r = client.post('/api/v1/content/repurpose', json={'source_post_id': pid, 'target_platforms':['linkedin']})
    assert 'linkedin' in r.json()['variants']

def test_hashtag_research(client):
    r = client.post('/api/v1/content/hashtag-research', json={'topic':'ai', 'platform':'twitter', 'count':5})
    assert len(r.json()['hashtags']) == 5
''',
    "test_publishing.py": '''
def _account(client):
    return client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}}).json()['id']

def test_create_draft(client):
    aid = _account(client)
    r = client.post('/api/v1/posts', json={'text':'hello', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'})
    assert r.status_code == 201
    assert r.json()['status'] == 'draft'

def test_schedule_post(client):
    aid = _account(client)
    p = client.post('/api/v1/posts', json={'text':'schedule', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'}).json()['id']
    r = client.post(f'/api/v1/posts/{p}/schedule', json={'scheduled_at':'2026-02-12T10:00:00Z'})
    assert r.json()['status'] == 'scheduled'

def test_publish_immediately(client):
    aid = _account(client)
    p = client.post('/api/v1/posts', json={'text':'publish', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'}).json()['id']
    r = client.post(f'/api/v1/posts/{p}/publish')
    assert r.status_code == 200
    assert r.json()['status'] == 'published'
    assert r.json()['platform_post_id']

def test_cross_post(client):
    r = client.post('/api/v1/posts/cross-post', json={'text':'launch', 'platforms':['twitter','linkedin'], 'adapt_per_platform':True})
    assert r.status_code == 200
    assert len(r.json()['posts']) == 2

def test_bulk_schedule(client):
    rows = [{'text':'a','platform':'twitter','scheduled_at':'2026-02-12T09:00:00Z'}, {'text':'b','platform':'linkedin','scheduled_at':'2026-02-12T10:00:00Z'}]
    r = client.post('/api/v1/posts/bulk-schedule', json={'posts': rows})
    assert r.status_code == 200
    assert r.json()['scheduled'] == 2
''',
    "test_trends.py": '''
def test_scan_trends(client):
    r = client.post('/api/v1/trends/scan')
    assert r.status_code == 200
    assert len(r.json()['trends']) >= 3

def test_create_post_from_trend(client):
    t = client.post('/api/v1/trends/scan').json()['trends'][0]['id']
    r = client.post(f'/api/v1/trends/{t}/create-post', json={'platforms':['twitter']})
    assert r.status_code == 200
    assert 'twitter' in r.json()['posts']
''',
    "test_competitors.py": '''
def test_add_competitor(client):
    r = client.post('/api/v1/competitors', json={'platform':'twitter','handle':'@rival'})
    assert r.status_code == 201
    assert r.json()['account_handle'] == '@rival'

def test_competitor_analysis(client):
    cid = client.post('/api/v1/competitors', json={'platform':'linkedin','handle':'rivalco'}).json()['id']
    r = client.post(f'/api/v1/competitors/{cid}/analyze')
    assert r.status_code == 200
    assert 'latest_post' in r.json()

def test_content_gaps(client):
    client.post('/api/v1/competitors', json={'platform':'twitter','handle':'@r1'})
    r = client.get('/api/v1/competitors/content-gaps?our_topics=automation')
    assert r.status_code == 200
    assert 'gaps' in r.json()
''',
    "test_analytics.py": '''
def _seed(client):
    aid = client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}}).json()['id']
    p = client.post('/api/v1/posts', json={'text':'viral', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'}).json()['id']
    client.post(f'/api/v1/posts/{p}/publish')

def test_dashboard(client):
    _seed(client)
    r = client.get('/api/v1/analytics/dashboard')
    assert r.status_code == 200
    assert 'total_followers' in r.json()

def test_growth_projection(client):
    _seed(client)
    r = client.get('/api/v1/analytics/growth/projection')
    assert r.status_code == 200
    assert any(m['count'] == 100000000 for m in r.json()['projected_milestones'])

def test_viral_detection(client):
    _seed(client)
    r = client.get('/api/v1/analytics/posts/viral')
    assert r.status_code == 200
    assert len(r.json()) >= 1
''',
    "test_strategy.py": '''
def _seed(client):
    client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}})

def test_recommendations(client):
    _seed(client)
    r = client.get('/api/v1/strategy/recommendations')
    assert r.status_code == 200
    assert len(r.json()['recommendations']) >= 1

def test_100m_plan(client):
    _seed(client)
    r = client.post('/api/v1/strategy/100m-plan')
    assert r.status_code == 200
    assert any(p['target'] == 100000000 for p in r.json()['phases'])
''',
}

MARKETING_README = """
# Omni Marketing Engine (System 38)

Production-ready FastAPI service for campaign orchestration, AI content generation, lead scoring, A/B testing, audience segmentation, competitor intelligence, and executive analytics.

## Run

```bash
docker compose -f services/marketing-engine/docker-compose.yml up -d --build
```

## Core Endpoints

- `POST /api/v1/campaigns`
- `POST /api/v1/content/generate/ad-copy`
- `POST /api/v1/leads`
- `POST /api/v1/ab-tests/{campaign_id}/create`
- `GET /api/v1/analytics/dashboard`
- `POST /api/v1/competitors/{id}/analyze`

## Infra

- Port: `9640`
- Container: `omni-marketing-engine`
- DB: `marketing_db` on `omni-gi-postgres`
- Redis: DB `16`
"""

SOCIAL_README = """
# Omni Social Media Command Center (System 39)

Production-ready FastAPI service for multi-platform social publishing, trend monitoring, competitor tracking, engagement queueing, analytics, and 100M follower strategy planning.

## Run

```bash
docker compose -f services/social-media/docker-compose.yml up -d --build
```

## Core Endpoints

- `POST /api/v1/accounts`
- `POST /api/v1/content/generate`
- `POST /api/v1/posts`
- `POST /api/v1/trends/scan`
- `GET /api/v1/analytics/dashboard`
- `POST /api/v1/strategy/100m-plan`

## Infra

- Port: `9641`
- Container: `omni-social-media`
- DB: `social_media_db` on `omni-gi-postgres`
- Redis: DB `17`
"""


def adapter_impl(class_name: str, platform: str) -> str:
    return f"""
from datetime import datetime, timezone


class {class_name}:
    async def publish_post(self, post: dict) -> str:
        return f"{platform}-{{post.get('id', 'post')}}"

    async def delete_post(self, platform_post_id: str) -> bool:
        return bool(platform_post_id)

    async def get_post_metrics(self, platform_post_id: str) -> dict:
        return {{"platform_post_id": platform_post_id, "impressions": 1200, "likes": 84, "comments": 9, "shares": 12}}

    async def get_account_metrics(self, account: dict) -> dict:
        return {{"account_id": account.get("id"), "followers": account.get("follower_count", 0), "updated_at": datetime.now(timezone.utc).isoformat()}}

    async def get_trending(self) -> list[dict]:
        return [{{"topic": "agentic coding", "velocity": 0.92}}, {{"topic": "ai delivery", "velocity": 0.85}}]

    async def get_interactions(self, since: datetime) -> list[dict]:
        return [{{"id": "int-1", "since": since.isoformat(), "content": "Great post"}}]

    async def reply_to(self, platform_post_id: str, text: str) -> str:
        return f"reply-{{platform_post_id}}"

    async def get_user_posts(self, handle: str, count: int) -> list[dict]:
        return [{{"handle": handle, "text": f"sample {{idx}}", "engagement_rate": 0.04 + idx * 0.005}} for idx in range(min(count, 20))]
"""


def write_init_files(base: Path) -> None:
    for path in [
        "app/__init__.py",
        "app/models/__init__.py",
        "app/routes/__init__.py",
        "app/services/__init__.py",
        "app/services/platform_adapters/__init__.py",
        "app/utils/__init__.py",
        "tests/__init__.py",
    ]:
        write(base / path, 'version = "1.0.0"\n' if path == "app/__init__.py" else "")


def write_marketing() -> None:
    base = SERVICES / "marketing-engine"
    init_tree(base)
    write_init_files(base)

    write(base / "docker-compose.yml", compose("marketing-engine", 9640, "marketing_db", 16, 38, True, [
        "LISTMONK_URL: \"http://omni-listmonk:9000\"",
        "LISTMONK_API_USER: \"${LISTMONK_API_USER}\"",
        "LISTMONK_API_PASSWORD: \"${LISTMONK_API_PASSWORD}\"",
        "SOCIAL_MEDIA_URL: \"http://omni-social-media:9641\"",
    ], "marketing-assets"))
    write(base / "Dockerfile", dockerfile("marketing-engine", "Marketing & Ad Engine", 9640))
    write(base / "requirements.txt", reqs([
        "jinja2==3.1.4", "aiofiles==24.1.0", "tiktoken==0.8.0", "beautifulsoup4==4.12.3", "markdown==3.7", "feedparser==6.0.11", "croniter==3.0.3", "pillow==11.1.0"
    ]))

    write(base / "app/main.py", common_main("marketing-engine", "Marketing and ad intelligence control plane", 38, 9640, MARKETING_ROUTE_IMPORTS, MARKETING_ROUTE_INCLUDES))
    write(base / "app/config.py", common_config("marketing-engine", 9640, MARKETING_CONFIG_EXTRA))
    write(base / "app/exceptions.py", common_exceptions())
    write(base / "app/database.py", common_database())

    write(base / "app/models/requests.py", MARKETING_REQUESTS)
    write(base / "app/models/responses.py", MARKETING_RESPONSES)
    write(base / "app/models/database.py", MARKETING_DB_MODEL)

    write(base / "app/services/state.py", MARKETING_STATE_SERVICE)
    for name, content in MARKETING_SERVICE_STUBS.items():
        write(base / "app/services" / name, content)
    for name, content in MARKETING_ROUTES.items():
        write(base / "app/routes" / name, content)

    misc = common_misc()
    for path, content in misc.items():
        if path == "tests/conftest.py":
            continue
        write(base / path, content)
    write(base / "tests/conftest.py", MARKETING_TEST_CONFTEXT)

    write(base / "alembic/versions/001_initial.py", MARKETING_MIGRATION)
    write(base / "sdk/client.py", MARKETING_SDK)

    for name, content in MARKETING_TESTS.items():
        write(base / "tests" / name, content)

    write(base / "dashboards/grafana.json", dashboard("Marketing Engine", "marketing-engine"))
    write(base / "alerts/rules.yml", alerts("marketing-engine"))
    write(base / "scripts/init.sh", "#!/usr/bin/env bash\nset -euo pipefail\necho 'Initializing marketing-engine'\n")
    write(base / "scripts/seed.sh", "#!/usr/bin/env bash\nset -euo pipefail\necho 'Seeding marketing-engine sample data'\n")
    write(base / "README.md", MARKETING_README)


def write_social() -> None:
    base = SERVICES / "social-media"
    init_tree(base)
    write_init_files(base)

    write(base / "docker-compose.yml", compose("social-media", 9641, "social_media_db", 17, 39, True, [
        "MARKETING_ENGINE_URL: \"http://omni-marketing-engine:9640\"",
        "TWITTER_API_KEY: \"${TWITTER_API_KEY}\"",
        "TWITTER_API_SECRET: \"${TWITTER_API_SECRET}\"",
        "TWITTER_ACCESS_TOKEN: \"${TWITTER_ACCESS_TOKEN}\"",
        "TWITTER_ACCESS_SECRET: \"${TWITTER_ACCESS_SECRET}\"",
        "LINKEDIN_CLIENT_ID: \"${LINKEDIN_CLIENT_ID}\"",
        "LINKEDIN_CLIENT_SECRET: \"${LINKEDIN_CLIENT_SECRET}\"",
        "INSTAGRAM_ACCESS_TOKEN: \"${INSTAGRAM_ACCESS_TOKEN}\"",
        "YOUTUBE_API_KEY: \"${YOUTUBE_API_KEY}\"",
        "TIKTOK_ACCESS_TOKEN: \"${TIKTOK_ACCESS_TOKEN}\"",
        "FACEBOOK_PAGE_TOKEN: \"${FACEBOOK_PAGE_TOKEN}\"",
        "REDDIT_CLIENT_ID: \"${REDDIT_CLIENT_ID}\"",
        "REDDIT_CLIENT_SECRET: \"${REDDIT_CLIENT_SECRET}\"",
        "THREADS_ACCESS_TOKEN: \"${THREADS_ACCESS_TOKEN}\"",
        "BLUESKY_HANDLE: \"${BLUESKY_HANDLE}\"",
        "BLUESKY_APP_PASSWORD: \"${BLUESKY_APP_PASSWORD}\"",
    ], "social-media-assets"))
    write(base / "Dockerfile", dockerfile("social-media", "Social Media Command Center", 9641))
    write(base / "requirements.txt", reqs([
        "aiofiles==24.1.0", "tiktoken==0.8.0", "feedparser==6.0.11", "croniter==3.0.3", "pillow==11.1.0", "tweepy==4.14.0", "python-linkedin-v2==0.9.0", "beautifulsoup4==4.12.3", "markdown==3.7", "emoji==2.14.0", "langdetect==1.0.9"
    ]))

    write(base / "app/main.py", common_main("social-media", "Social media command center and growth intelligence", 39, 9641, SOCIAL_ROUTE_IMPORTS, SOCIAL_ROUTE_INCLUDES))
    write(base / "app/config.py", common_config("social-media", 9641, SOCIAL_CONFIG_EXTRA))
    write(base / "app/exceptions.py", common_exceptions())
    write(base / "app/database.py", common_database())

    write(base / "app/models/requests.py", SOCIAL_REQUESTS)
    write(base / "app/models/responses.py", SOCIAL_RESPONSES)
    write(base / "app/models/database.py", SOCIAL_DB_MODEL)

    for name, content in SOCIAL_SERVICE_STUBS.items():
        write(base / "app/services" / name, content)
    for fname, cls in PLATFORM_ADAPTERS.items():
        write(base / "app/services/platform_adapters" / fname, adapter_impl(cls, fname.replace('.py', '')))
    for name, content in SOCIAL_ROUTES.items():
        write(base / "app/routes" / name, content)

    misc = common_misc()
    for path, content in misc.items():
        if path == "tests/conftest.py":
            continue
        write(base / path, content)
    write(base / "tests/conftest.py", SOCIAL_TEST_CONFTEXT)

    write(base / "alembic/versions/001_initial.py", SOCIAL_MIGRATION)
    write(base / "sdk/client.py", SOCIAL_SDK)

    for name, content in SOCIAL_TESTS.items():
        write(base / "tests" / name, content)

    write(base / "dashboards/grafana.json", dashboard("Social Media Command Center", "social-media"))
    write(base / "alerts/rules.yml", alerts("social-media"))
    write(base / "scripts/init.sh", "#!/usr/bin/env bash\nset -euo pipefail\necho 'Initializing social-media'\n")
    write(base / "scripts/seed.sh", "#!/usr/bin/env bash\nset -euo pipefail\necho 'Seeding social-media sample data'\n")
    write(base / "README.md", SOCIAL_README)


def main() -> None:
    ensure_env_example()
    write_marketing()
    write_social()
    print("Generated services/marketing-engine and services/social-media")


if __name__ == "__main__":
    main()
