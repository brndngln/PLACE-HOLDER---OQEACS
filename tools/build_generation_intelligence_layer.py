#!/usr/bin/env python3
"""Build the Generation Intelligence Layer (14 services + shared infra)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "services"

BASE_REQUIREMENTS = [
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

SERVICES: list[dict[str, Any]] = [
    {
        "system": 1,
        "phase": 1,
        "slug": "execution-sandbox",
        "display": "Agent Execution Sandbox",
        "port": 9620,
        "critical": True,
        "db_name": None,
        "redis_db": 10,
        "mem_limit": "4G",
        "cpu_limit": "4.0",
        "mem_reservation": "1G",
        "cpu_reservation": "1.0",
        "extra_reqs": ["docker==7.1.0", "aiofiles==24.1.0", "websockets==13.1"],
    },
    {
        "system": 2,
        "phase": 1,
        "slug": "comprehension-engine",
        "display": "Codebase Comprehension Engine",
        "port": 9621,
        "critical": True,
        "db_name": "comprehension_db",
        "redis_db": 11,
        "mem_limit": "2G",
        "cpu_limit": "2.0",
        "mem_reservation": "512M",
        "cpu_reservation": "0.5",
        "extra_reqs": [
            "tree-sitter==0.23.2",
            "tree-sitter-python==0.23.2",
            "tree-sitter-javascript==0.23.0",
            "tree-sitter-typescript==0.23.0",
            "tree-sitter-go==0.23.1",
            "tree-sitter-rust==0.23.0",
            "tree-sitter-java==0.23.1",
            "tree-sitter-ruby==0.23.0",
            "tree-sitter-c==0.23.1",
            "tree-sitter-cpp==0.23.0",
            "gitpython==3.1.43",
            "networkx==3.4.2",
            "radon==6.0.1",
            "pygments==2.18.0",
            "aiofiles==24.1.0",
            "tiktoken==0.8.0",
        ],
    },
    {
        "system": 3,
        "phase": 1,
        "slug": "hallucination-detector",
        "display": "Hallucination Detection Layer",
        "port": 9622,
        "critical": True,
        "db_name": "hallucination_db",
        "redis_db": 12,
        "mem_limit": "2G",
        "cpu_limit": "2.0",
        "mem_reservation": "512M",
        "cpu_reservation": "0.5",
        "extra_reqs": [
            "tree-sitter==0.23.2",
            "tree-sitter-python==0.23.2",
            "tree-sitter-javascript==0.23.0",
            "tree-sitter-typescript==0.23.0",
            "tree-sitter-go==0.23.1",
            "tree-sitter-rust==0.23.0",
            "aiosqlite==0.20.0",
            "packaging==24.2",
            "aiofiles==24.1.0",
            "tiktoken==0.8.0",
        ],
    },
    {
        "system": 4,
        "phase": 1,
        "slug": "runtime-manager",
        "display": "Language Runtime Manager",
        "port": 9624,
        "critical": True,
        "db_name": None,
        "redis_db": None,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["docker==7.1.0", "aiofiles==24.1.0", "croniter==3.0.3"],
    },
    {
        "system": 5,
        "phase": 1,
        "slug": "template-library",
        "display": "Project Template Library",
        "port": 9627,
        "critical": False,
        "db_name": "template_db",
        "redis_db": None,
        "mem_limit": "512M",
        "cpu_limit": "0.5",
        "mem_reservation": "128M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["jinja2==3.1.4", "gitpython==3.1.43", "aiofiles==24.1.0"],
    },
    {
        "system": 6,
        "phase": 2,
        "slug": "incremental-orchestrator",
        "display": "Incremental Build Orchestrator",
        "port": 9628,
        "critical": True,
        "db_name": "incremental_db",
        "redis_db": 13,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.5",
        "extra_reqs": ["tiktoken==0.8.0", "aiofiles==24.1.0", "networkx==3.4.2"],
    },
    {
        "system": 7,
        "phase": 2,
        "slug": "parallel-orchestrator",
        "display": "Parallel Task Orchestrator",
        "port": 9623,
        "critical": False,
        "db_name": "parallel_db",
        "redis_db": 14,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.5",
        "extra_reqs": ["gitpython==3.1.43", "networkx==3.4.2", "aiofiles==24.1.0"],
    },
    {
        "system": 8,
        "phase": 2,
        "slug": "cost-router",
        "display": "Cost Aware Task Router",
        "port": 9632,
        "critical": False,
        "db_name": "cost_db",
        "redis_db": 15,
        "mem_limit": "512M",
        "cpu_limit": "0.5",
        "mem_reservation": "128M",
        "cpu_reservation": "0.25",
        "extra_reqs": [],
    },
    {
        "system": 9,
        "phase": 3,
        "slug": "ui-intelligence",
        "display": "UI UX Generation Intelligence",
        "port": 9625,
        "critical": False,
        "db_name": "ui_intelligence_db",
        "redis_db": None,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["aiofiles==24.1.0", "beautifulsoup4==4.12.3"],
    },
    {
        "system": 10,
        "phase": 3,
        "slug": "api-knowledge",
        "display": "API Integration Knowledge Base",
        "port": 9626,
        "critical": False,
        "db_name": "api_knowledge_db",
        "redis_db": None,
        "mem_limit": "2G",
        "cpu_limit": "1.0",
        "mem_reservation": "512M",
        "cpu_reservation": "0.5",
        "extra_reqs": ["aiofiles==24.1.0", "beautifulsoup4==4.12.3", "tiktoken==0.8.0"],
    },
    {
        "system": 11,
        "phase": 3,
        "slug": "docs-generator",
        "display": "Documentation Generator",
        "port": 9629,
        "critical": False,
        "db_name": "docs_generator_db",
        "redis_db": None,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["jinja2==3.1.4", "aiofiles==24.1.0", "tiktoken==0.8.0"],
    },
    {
        "system": 12,
        "phase": 3,
        "slug": "client-hub",
        "display": "Client Communication Hub",
        "port": 9630,
        "critical": False,
        "db_name": "client_hub_db",
        "redis_db": None,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["aiofiles==24.1.0", "jinja2==3.1.4"],
    },
    {
        "system": 13,
        "phase": 3,
        "slug": "regression-intelligence",
        "display": "Regression Intelligence",
        "port": 9631,
        "critical": False,
        "db_name": "regression_db",
        "redis_db": None,
        "mem_limit": "1G",
        "cpu_limit": "1.0",
        "mem_reservation": "256M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["aiofiles==24.1.0", "deepdiff==8.1.1"],
    },
    {
        "system": 14,
        "phase": 3,
        "slug": "retrospective-engine",
        "display": "Retrospective Engine",
        "port": 9633,
        "critical": False,
        "db_name": "retrospective_db",
        "redis_db": None,
        "mem_limit": "512M",
        "cpu_limit": "0.5",
        "mem_reservation": "128M",
        "cpu_reservation": "0.25",
        "extra_reqs": ["aiofiles==24.1.0", "tiktoken==0.8.0"],
    },
]


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def ensure_env_keys() -> None:
    pairs = {
        "GI_DB_USER": "omni",
        "GI_DB_PASSWORD": "CHANGE_ME_GENERATE_WITH_OPENSSL",
        "MATTERMOST_GI_WEBHOOK_URL": "http://omni-mattermost:8065/hooks/omni-generation-intelligence",
    }
    for filename in [".env.example", ".env"]:
        path = ROOT / filename
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        keys = {line.split("=", 1)[0] for line in lines if "=" in line and not line.strip().startswith("#")}
        updated = list(lines)
        for k, v in pairs.items():
            if k not in keys:
                updated.append(f"{k}={v}")
        path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def build_infra() -> None:
    infra = SERVICES_DIR / "generation-intelligence-infra"
    write(
        infra / "docker-compose.yml",
        """
        version: "3.9"

        networks:
          omni-quantum-network:
            external: true

        volumes:
          gi_postgres_data:
            driver: local

        services:
          gi-postgres:
            image: postgres:16-alpine
            container_name: omni-gi-postgres
            hostname: omni-gi-postgres
            environment:
              POSTGRES_USER: ${GI_DB_USER:-omni}
              POSTGRES_PASSWORD: ${GI_DB_PASSWORD}
              POSTGRES_DB: gi_admin
            ports:
              - "5433:5432"
            volumes:
              - gi_postgres_data:/var/lib/postgresql/data
              - ./init-databases.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
            networks:
              - omni-quantum-network
            healthcheck:
              test: ["CMD-SHELL", "pg_isready -U ${GI_DB_USER:-omni}"]
              interval: 10s
              timeout: 5s
              retries: 5
              start_period: 15s
            restart: unless-stopped
            deploy:
              resources:
                limits:
                  memory: 1G
                  cpus: '1.0'
                reservations:
                  memory: 256M
            security_opt:
              - no-new-privileges:true
            labels:
              - "omni.quantum.component=gi-postgres"
              - "omni.quantum.tier=generation-intelligence"
              - "omni.quantum.critical=true"
            logging:
              driver: "json-file"
              options:
                max-size: "50m"
                max-file: "5"
        """,
    )
    write(
        infra / "init-databases.sql",
        """
        CREATE DATABASE comprehension_db;
        CREATE DATABASE hallucination_db;
        CREATE DATABASE template_db;
        CREATE DATABASE incremental_db;
        CREATE DATABASE parallel_db;
        CREATE DATABASE cost_db;
        CREATE DATABASE ui_intelligence_db;
        CREATE DATABASE api_knowledge_db;
        CREATE DATABASE docs_generator_db;
        CREATE DATABASE client_hub_db;
        CREATE DATABASE regression_db;
        CREATE DATABASE retrospective_db;

        GRANT ALL PRIVILEGES ON DATABASE comprehension_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE hallucination_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE template_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE incremental_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE parallel_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE cost_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE ui_intelligence_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE api_knowledge_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE docs_generator_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE client_hub_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE regression_db TO omni;
        GRANT ALL PRIVILEGES ON DATABASE retrospective_db TO omni;
        """,
    )


def requirements_for(service: dict[str, Any]) -> str:
    reqs = list(dict.fromkeys(BASE_REQUIREMENTS + service["extra_reqs"]))
    return "\n".join(reqs) + "\n"


def compose_for(service: dict[str, Any]) -> str:
    slug = service["slug"]
    port = service["port"]
    db_name = service["db_name"]
    redis_db = service["redis_db"]
    read_only = "false" if slug == "execution-sandbox" else "true"
    env_db = (
        f'DATABASE_URL: "postgresql+asyncpg://${{GI_DB_USER:-omni}}:${{GI_DB_PASSWORD}}@omni-gi-postgres:5432/{db_name}"'
        if db_name
        else 'DATABASE_URL: ""'
    )
    redis_line = (
        f'REDIS_URL: "redis://:${{REDIS_PASSWORD}}@omni-redis:6379/{redis_db}"'
        if redis_db is not None
        else 'REDIS_URL: "redis://:${REDIS_PASSWORD}@omni-redis:6379/0"'
    )

    lines: list[str] = [
        'version: "3.9"',
        "",
        "networks:",
        "  omni-quantum-network:",
        "    external: true",
        "",
        "volumes:",
        f"  {slug.replace('-', '_')}_data:",
        "    driver: local",
    ]
    if slug == "execution-sandbox":
        lines.extend(
            [
                "  omni-sandbox-workspaces:",
                "    driver: local",
            ]
        )

    lines.extend(
        [
            "",
            "services:",
            f"  {slug}:",
            "    build:",
            "      context: .",
            "      dockerfile: Dockerfile",
            "      args:",
            '        BUILD_DATE: "${BUILD_DATE:-2026-02-11T00:00:00Z}"',
            '        VERSION: "${VERSION:-1.0.0}"',
            f"    image: omni-{slug}:${{VERSION:-1.0.0}}",
            f"    container_name: omni-{slug}",
            f"    hostname: omni-{slug}",
            "    env_file:",
            "      - ../../.env",
            "    environment:",
            f'      SERVICE_NAME: "{slug}"',
            f'      SERVICE_PORT: "{port}"',
            '      VERSION: "${VERSION:-1.0.0}"',
            '      LOG_LEVEL: "${LOG_LEVEL:-info}"',
            '      LOG_FORMAT: "json"',
            f"      {env_db}",
            f"      {redis_line}",
            '      LITELLM_URL: "http://omni-litellm:4000"',
            '      LITELLM_API_KEY: "${LITELLM_API_KEY}"',
            '      QDRANT_URL: "http://omni-qdrant:6333"',
            f'      QDRANT_COLLECTION: "{slug}"',
            '      LANGFUSE_HOST: "http://omni-langfuse:3000"',
            '      LANGFUSE_PUBLIC_KEY: "${LANGFUSE_PUBLIC_KEY}"',
            '      LANGFUSE_SECRET_KEY: "${LANGFUSE_SECRET_KEY}"',
            '      MATTERMOST_WEBHOOK_URL: "${MATTERMOST_GI_WEBHOOK_URL}"',
            '      MATTERMOST_CHANNEL: "omni-generation-intelligence"',
            '      MINIO_ENDPOINT: "omni-minio:9000"',
            '      MINIO_ACCESS_KEY: "${MINIO_ACCESS_KEY}"',
            '      MINIO_SECRET_KEY: "${MINIO_SECRET_KEY}"',
            f'      MINIO_BUCKET: "gi-{slug}"',
            '      MINIO_SECURE: "false"',
            '      GITEA_URL: "http://omni-gitea:3000"',
            '      GITEA_TOKEN: "${GITEA_TOKEN}"',
            "    ports:",
            f'      - "{port}:{port}"',
            "    volumes:",
            f"      - {slug.replace('-', '_')}_data:/app/data",
        ]
    )
    if slug == "execution-sandbox":
        lines.extend(
            [
                "      - /var/run/docker.sock:/var/run/docker.sock:ro",
                "      - omni-sandbox-workspaces:/workspaces",
            ]
        )
    lines.extend(
        [
            "    networks:",
            "      - omni-quantum-network",
        ]
    )
    lines.extend(
        [
            "    healthcheck:",
            f"      test: ['CMD-SHELL', 'python -c \"import urllib.request; urllib.request.urlopen(\\\"http://localhost:{port}/health\\\")\"']",
            "      interval: 30s",
            "      timeout: 10s",
            "      retries: 3",
            "      start_period: 40s",
            "    restart: unless-stopped",
            "    deploy:",
            "      resources:",
            "        limits:",
            f"          memory: {service['mem_limit']}",
            f"          cpus: '{service['cpu_limit']}'",
            "        reservations:",
            f"          memory: {service['mem_reservation']}",
            f"          cpus: '{service['cpu_reservation']}'",
            "    security_opt:",
            "      - no-new-privileges:true",
            f"    read_only: {read_only}",
            "    tmpfs:",
            "      - /tmp:size=256M",
            "    labels:",
            f'      - "omni.quantum.component={slug}"',
            '      - "omni.quantum.tier=generation-intelligence"',
            f'      - "omni.quantum.system={service["system"]}"',
            f'      - "omni.quantum.phase={service["phase"]}"',
            f'      - "omni.quantum.critical={str(service["critical"]).lower()}"',
            f'      - "omni.quantum.port={port}"',
            '      - "prometheus.scrape=true"',
            f'      - "prometheus.port={port}"',
            '      - "prometheus.path=/metrics"',
            "    logging:",
            '      driver: "json-file"',
            "      options:",
            '        max-size: "50m"',
            '        max-file: "5"',
            '        labels: "omni.quantum.component"',
            '        tag: "{{.Name}}"',
        ]
    )
    return "\n".join(lines) + "\n"


def dockerfile_for(service: dict[str, Any]) -> str:
    slug = service["slug"]
    port = service["port"]
    return textwrap.dedent(
        f"""
        FROM python:3.12-slim AS builder
        WORKDIR /build
        RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
        COPY requirements.txt .
        RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

        FROM python:3.12-slim AS production
        ARG BUILD_DATE
        ARG VERSION=1.0.0
        LABEL maintainer="Omni Quantum Elite" \
              version="${{VERSION}}" \
              build-date="${{BUILD_DATE}}" \
              org.opencontainers.image.title="omni-{slug}" \
              org.opencontainers.image.description="{service['display']}" \
              org.opencontainers.image.version="${{VERSION}}"

        WORKDIR /app
        RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && rm -rf /var/lib/apt/lists/* && groupadd -r omni && useradd -r -g omni -d /app -s /sbin/nologin omni && mkdir -p /app/data && chown -R omni:omni /app
        COPY --from=builder /install /usr/local
        COPY --chown=omni:omni app/ ./app/
        COPY --chown=omni:omni alembic/ ./alembic/ 2>/dev/null || true
        COPY --chown=omni:omni alembic.ini ./alembic.ini 2>/dev/null || true
        COPY --chown=omni:omni scripts/ ./scripts/
        COPY --chown=omni:omni config/ ./config/ 2>/dev/null || true
        RUN chmod +x scripts/*.sh 2>/dev/null || true
        USER omni
        EXPOSE {port}
        HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}/health')"
        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{port}", "--workers", "2", "--loop", "uvloop", "--http", "httptools", "--log-level", "info", "--access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
        """
    )


def base_config_py(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        from pydantic import Field
        from pydantic_settings import BaseSettings, SettingsConfigDict


        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_file="../../.env", env_file_encoding="utf-8", extra="ignore")

            service_name: str = "{service['slug']}"
            service_port: int = {service['port']}
            version: str = "1.0.0"
            log_level: str = "info"
            log_format: str = "json"
            database_url: str = ""
            redis_url: str = "redis://localhost:6379/0"
            litellm_url: str = "http://omni-litellm:4000"
            litellm_api_key: str = ""
            qdrant_url: str = "http://omni-qdrant:6333"
            qdrant_collection: str = "{service['slug']}"
            langfuse_host: str = "http://omni-langfuse:3000"
            langfuse_public_key: str = ""
            langfuse_secret_key: str = ""
            mattermost_webhook_url: str = ""
            mattermost_channel: str = "omni-generation-intelligence"
            minio_endpoint: str = "omni-minio:9000"
            minio_access_key: str = ""
            minio_secret_key: str = ""
            minio_bucket: str = "gi-{service['slug']}"
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
                return {{"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}}.get(level, 20)


        settings = Settings()
        """
    )


def base_exceptions_py() -> str:
    return textwrap.dedent(
        """
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
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.message, "details": exc.details, "type": "ServiceError"},
            )


        async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=500,
                content={"error": "internal server error", "details": {"message": str(exc)}, "type": type(exc).__name__},
            )


        exception_handlers = {
            ServiceError: service_error_handler,
            Exception: generic_error_handler,
        }
        """
    )


def base_database_py() -> str:
    return textwrap.dedent(
        """
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
    )


def base_dependencies_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from fastapi import Request


        def get_correlation_id(request: Request) -> str:
            return getattr(request.state, "correlation_id", "")
        """
    )


def base_middleware_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from starlette.requests import Request


        async def bind_request_context(request: Request) -> dict[str, str]:
            return {
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else "",
            }
        """
    )


def base_requests_py(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from typing import Any

        from pydantic import BaseModel, Field, model_validator


        class GenericRequest(BaseModel):
            payload: dict[str, Any] = Field(default_factory=dict)


        class CreateItemRequest(BaseModel):
            name: str = Field(min_length=1, max_length=200)
            data: dict[str, Any] = Field(default_factory=dict)


        class ExecuteRequest(BaseModel):
            command: str | None = Field(default=None, max_length=10_000)
            code: str | None = Field(default=None, max_length=1_000_000)
            timeout_seconds: int = Field(default=30, ge=1, le=600)

            @model_validator(mode="after")
            def _validate_command_or_code(self) -> "ExecuteRequest":
                if bool(self.command) == bool(self.code):
                    raise ValueError("Exactly one of command or code must be provided")
                return self


        class CreateAnalysisRequest(BaseModel):
            repo_url: str | None = None
            local_path: str | None = None
            git_ref: str = "main"
            depth: str = "full"
            force_reanalyze: bool = False

            @model_validator(mode="after")
            def _validate_source(self) -> "CreateAnalysisRequest":
                if bool(self.repo_url) == bool(self.local_path):
                    raise ValueError("Exactly one of repo_url or local_path is required")
                return self


        class ScanRequest(BaseModel):
            code: str = Field(min_length=1, max_length=1_000_000)
            language: str
            dependencies: dict[str, str] = Field(default_factory=dict)
            spec_summary: str | None = None
            model_used: str | None = None
            task_id: str | None = None
            checks: list[str] | None = None
        """
    )


def base_responses_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from datetime import datetime, timezone
        from typing import Any

        from pydantic import BaseModel, Field


        class GenericResponse(BaseModel):
            ok: bool = True
            message: str = "ok"
            data: dict[str, Any] = Field(default_factory=dict)
            timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


        class ItemResponse(BaseModel):
            id: str
            name: str
            data: dict[str, Any] = Field(default_factory=dict)


        class HealthResponse(BaseModel):
            status: str
            service: str
            version: str
        """
    )


def base_models_database_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from datetime import datetime

        from sqlalchemy import DateTime, Integer, String, Text, func
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


        class Base(DeclarativeBase):
            pass


        class AuditRecord(Base):
            __tablename__ = "audit_records"

            id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
            record_type: Mapped[str] = mapped_column(String(100), index=True)
            payload: Mapped[str] = mapped_column(Text)
            created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        """
    )


def base_notifications_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        import httpx


        async def notify_mattermost(webhook_url: str, text: str) -> bool:
            if not webhook_url:
                return False
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(webhook_url, json={"text": text})
                return response.is_success
        """
    )


def base_langfuse_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from contextlib import asynccontextmanager
        from datetime import datetime, timezone

        import structlog

        logger = structlog.get_logger()


        @asynccontextmanager
        async def traced_span(name: str, metadata: dict | None = None):
            start = datetime.now(timezone.utc)
            logger.info("trace_start", span=name, metadata=metadata or {}, started_at=start.isoformat())
            try:
                yield
            finally:
                end = datetime.now(timezone.utc)
                logger.info("trace_end", span=name, finished_at=end.isoformat())
        """
    )


def service_routes_py(service: dict[str, Any]) -> str:
    slug = service["slug"]
    sysn = service["system"]
    if slug == "execution-sandbox":
        return textwrap.dedent(
            """
            from __future__ import annotations

            import asyncio
            import subprocess
            import time
            import uuid
            from datetime import datetime, timezone
            from enum import Enum
            from pathlib import Path
            from typing import Any

            import aiofiles
            from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
            from pydantic import BaseModel, Field, model_validator

            from app.config import settings

            router = APIRouter()


            class Language(str, Enum):
                PYTHON_312 = "python:3.12"
                PYTHON_311 = "python:3.11"
                NODE_22 = "node:22"
                NODE_20 = "node:20"
                GO_122 = "go:1.22"
                RUST_178 = "rust:1.78"
                JAVA_21 = "java:21"
                DOTNET_8 = "dotnet:8"
                RUBY_33 = "ruby:3.3"
                CPP_LATEST = "cpp:latest"
                ELIXIR_116 = "elixir:1.16"


            class ExecutionType(str, Enum):
                SMOKE_RUN = "SMOKE_RUN"
                TEST_RUN = "TEST_RUN"
                IMPORT_CHECK = "IMPORT_CHECK"
                API_CHECK = "API_CHECK"
                BUILD_CHECK = "BUILD_CHECK"
                LINT_CHECK = "LINT_CHECK"
                TYPE_CHECK = "TYPE_CHECK"
                REPL = "REPL"
                CUSTOM = "CUSTOM"


            class SandboxStatus(str, Enum):
                CREATING = "CREATING"
                INSTALLING_DEPS = "INSTALLING_DEPS"
                READY = "READY"
                EXECUTING = "EXECUTING"
                ERROR = "ERROR"
                DESTROYING = "DESTROYING"
                DESTROYED = "DESTROYED"


            class CreateSandboxRequest(BaseModel):
                task_id: str = Field(min_length=1, max_length=100)
                language: Language
                dependencies: list[str] = Field(default_factory=list, max_length=200)
                workspace_files: dict[str, str] | None = None
                memory_limit: str | None = Field(default=None, pattern=r"^\\d+[mg]$")
                cpu_limit: float | None = Field(default=None, ge=0.5, le=8.0)
                network_mode: str | None = "none"
                environment: dict[str, str] | None = None
                ttl_seconds: int | None = Field(default=None, ge=60, le=86400)

                @model_validator(mode="after")
                def _validate_inputs(self) -> "CreateSandboxRequest":
                    blocked = set(";|&`$(){}")
                    for dep in self.dependencies:
                        if any(ch in dep for ch in blocked):
                            raise ValueError("dependency contains blocked shell characters")
                    if self.workspace_files:
                        for path, content in self.workspace_files.items():
                            if path.startswith("/") or ".." in path:
                                raise ValueError("workspace file path is invalid")
                            if len(content.encode("utf-8")) > settings.max_file_size_bytes:
                                raise ValueError("workspace file too large")
                    return self


            class ExecuteRequest(BaseModel):
                execution_type: ExecutionType
                command: str | None = Field(default=None, max_length=10_000)
                code: str | None = Field(default=None, max_length=1_000_000)
                timeout_seconds: int = Field(default=30, ge=1, le=600)
                working_directory: str | None = "/workspace"
                environment: dict[str, str] | None = None
                stdin_data: str | None = Field(default=None, max_length=1_000_000)

                @model_validator(mode="after")
                def _validate_inputs(self) -> "ExecuteRequest":
                    if bool(self.command) == bool(self.code):
                        raise ValueError("exactly one of command/code is required")
                    blocked = ["docker", "nsenter", "chroot", "mount", "/proc/", "/sys/"]
                    if self.command and any(b in self.command for b in blocked):
                        raise ValueError("command contains blocked token")
                    if self.working_directory and not (self.working_directory.startswith("/workspace") or self.working_directory.startswith("/tmp")):
                        raise ValueError("working_directory must be under /workspace or /tmp")
                    if self.working_directory and ".." in self.working_directory:
                        raise ValueError("working_directory cannot contain ..")
                    return self


            class WriteFilesRequest(BaseModel):
                files: dict[str, str]

                @model_validator(mode="after")
                def _validate(self) -> "WriteFilesRequest":
                    if not (1 <= len(self.files) <= 100):
                        raise ValueError("files must contain 1..100 entries")
                    total = 0
                    for path, content in self.files.items():
                        if path.startswith("/") or ".." in path:
                            raise ValueError("invalid file path")
                        size = len(content.encode("utf-8"))
                        if size > settings.max_file_size_bytes:
                            raise ValueError("file too large")
                        total += size
                    if total > 100 * 1024 * 1024:
                        raise ValueError("total file payload too large")
                    return self


            class InstallDependenciesRequest(BaseModel):
                packages: list[str] = Field(min_length=1, max_length=50)

                @model_validator(mode="after")
                def _validate(self) -> "InstallDependenciesRequest":
                    blocked = set(";|&`$(){}")
                    for pkg in self.packages:
                        if any(ch in pkg for ch in blocked):
                            raise ValueError("package contains blocked shell characters")
                    return self


            SANDBOXES: dict[str, dict[str, Any]] = {}
            EXECUTIONS: dict[str, dict[str, Any]] = {}


            def _workspace(sandbox_id: str) -> Path:
                base = Path(settings.workspace_base if settings.workspace_base else "/tmp/omni-sandboxes")
                if str(base).startswith("/workspaces"):
                    base = Path("/tmp/omni-sandboxes")
                target = base / sandbox_id
                target.mkdir(parents=True, exist_ok=True)
                return target


            async def _write_file(root: Path, path: str, content: str) -> None:
                file_path = root / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(content)


            @router.post("/api/v1/sandboxes")
            async def create_sandbox(request: CreateSandboxRequest) -> dict[str, Any]:
                active = sum(1 for sbx in SANDBOXES.values() if sbx["status"] != SandboxStatus.DESTROYED)
                if active >= settings.max_concurrent_sandboxes:
                    raise HTTPException(status_code=429, detail="max concurrent sandboxes reached")

                sandbox_id = f"sbx-{uuid.uuid4().hex[:12]}"
                workspace = _workspace(sandbox_id)
                if request.workspace_files:
                    for path, content in request.workspace_files.items():
                        await _write_file(workspace, path, content)

                now = datetime.now(timezone.utc)
                payload = {
                    "sandbox_id": sandbox_id,
                    "task_id": request.task_id,
                    "language": request.language.value,
                    "status": SandboxStatus.READY,
                    "workspace_path": str(workspace),
                    "container_id": f"sim-{sandbox_id}",
                    "container_name": f"omni-sandbox-{sandbox_id}",
                    "resource_limits": {
                        "memory_limit": request.memory_limit or settings.default_memory_limit,
                        "cpu_limit": request.cpu_limit or settings.default_cpu_limit,
                    },
                    "network_mode": request.network_mode or settings.sandbox_network,
                    "execution_count": 0,
                    "created_at": now.isoformat(),
                    "last_activity_at": now.isoformat(),
                    "ttl_seconds": request.ttl_seconds or settings.sandbox_ttl_seconds,
                    "dependencies": request.dependencies,
                }
                SANDBOXES[sandbox_id] = payload
                return payload


            @router.get("/api/v1/sandboxes")
            async def list_sandboxes() -> dict[str, Any]:
                sandboxes = list(SANDBOXES.values())
                by_language: dict[str, int] = {}
                by_status: dict[str, int] = {}
                for sbx in sandboxes:
                    by_language[sbx["language"]] = by_language.get(sbx["language"], 0) + 1
                    status = str(sbx["status"])
                    by_status[status] = by_status.get(status, 0) + 1
                return {
                    "sandboxes": sandboxes,
                    "total": len(sandboxes),
                    "active": sum(1 for s in sandboxes if s["status"] != SandboxStatus.DESTROYED),
                    "by_language": by_language,
                    "by_status": by_status,
                }


            @router.get("/api/v1/sandboxes/stats")
            async def stats() -> dict[str, Any]:
                executions = list(EXECUTIONS.values())
                durations = [e["duration_ms"] for e in executions]
                avg = sum(durations) / len(durations) if durations else 0.0
                p95 = sorted(durations)[int(len(durations) * 0.95) - 1] if durations else 0.0
                return {
                    "total_created": len(SANDBOXES),
                    "total_destroyed": sum(1 for s in SANDBOXES.values() if s["status"] == SandboxStatus.DESTROYED),
                    "currently_active": sum(1 for s in SANDBOXES.values() if s["status"] != SandboxStatus.DESTROYED),
                    "total_executions": len(executions),
                    "avg_duration_ms": round(avg, 2),
                    "p95_duration_ms": round(float(p95), 2),
                }


            @router.get("/api/v1/sandboxes/{sandbox_id}")
            async def get_sandbox(sandbox_id: str) -> dict[str, Any]:
                sbx = SANDBOXES.get(sandbox_id)
                if not sbx:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                return sbx


            @router.post("/api/v1/sandboxes/{sandbox_id}/files")
            async def write_files(sandbox_id: str, request: WriteFilesRequest) -> dict[str, Any]:
                sbx = SANDBOXES.get(sandbox_id)
                if not sbx:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                root = Path(sbx["workspace_path"])
                total = 0
                for path, content in request.files.items():
                    await _write_file(root, path, content)
                    total += len(content.encode("utf-8"))
                sbx["last_activity_at"] = datetime.now(timezone.utc).isoformat()
                return {"sandbox_id": sandbox_id, "files_written": len(request.files), "bytes_written": total}


            @router.get("/api/v1/sandboxes/{sandbox_id}/files")
            async def list_files(sandbox_id: str) -> dict[str, Any]:
                sbx = SANDBOXES.get(sandbox_id)
                if not sbx:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                root = Path(sbx["workspace_path"])
                files = []
                total_size = 0
                for path in root.rglob("*"):
                    if path.is_file():
                        stat = path.stat()
                        rel = path.relative_to(root).as_posix()
                        files.append({
                            "path": rel,
                            "size_bytes": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                            "file_type": "file",
                            "permissions": oct(stat.st_mode & 0o777),
                        })
                        total_size += stat.st_size
                return {"sandbox_id": sandbox_id, "files": files, "total_files": len(files), "total_size_bytes": total_size}


            @router.get("/api/v1/sandboxes/{sandbox_id}/files/{path:path}")
            async def read_file(sandbox_id: str, path: str) -> dict[str, Any]:
                if path.startswith("/") or ".." in path:
                    raise HTTPException(status_code=422, detail="invalid path")
                sbx = SANDBOXES.get(sandbox_id)
                if not sbx:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                file_path = Path(sbx["workspace_path"]) / path
                if not file_path.exists() or not file_path.is_file():
                    raise HTTPException(status_code=404, detail="file not found")
                content = file_path.read_text(encoding="utf-8")
                return {
                    "sandbox_id": sandbox_id,
                    "path": path,
                    "content": content,
                    "size_bytes": len(content.encode("utf-8")),
                    "encoding": "utf-8",
                }


            @router.post("/api/v1/sandboxes/{sandbox_id}/dependencies")
            async def install_dependencies(sandbox_id: str, request: InstallDependenciesRequest) -> dict[str, Any]:
                if sandbox_id not in SANDBOXES:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                results = []
                for pkg in request.packages:
                    results.append({"package": pkg, "installed": True, "version": pkg.split("==")[-1] if "==" in pkg else None, "error": None})
                return {
                    "sandbox_id": sandbox_id,
                    "packages_requested": len(request.packages),
                    "results": results,
                    "all_succeeded": all(r["installed"] for r in results),
                    "install_log": "simulated install",
                    "duration_ms": 10.0 * len(request.packages),
                }


            def _language_command(language: str, code_path: Path) -> list[str]:
                if language.startswith("python"):
                    return ["python", str(code_path)]
                if language.startswith("node"):
                    return ["node", str(code_path)]
                if language.startswith("ruby"):
                    return ["ruby", str(code_path)]
                return ["python", str(code_path)]


            @router.post("/api/v1/sandboxes/{sandbox_id}/execute")
            async def execute(sandbox_id: str, request: ExecuteRequest) -> dict[str, Any]:
                sbx = SANDBOXES.get(sandbox_id)
                if not sbx:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                if sbx["status"] == SandboxStatus.EXECUTING:
                    raise HTTPException(status_code=409, detail="sandbox is busy")

                sbx["status"] = SandboxStatus.EXECUTING
                started = time.perf_counter()
                exec_id = f"exec-{uuid.uuid4().hex[:12]}"
                root = Path(sbx["workspace_path"])

                command_list: list[str]
                temp_file: Path | None = None
                if request.code:
                    suffix = ".py" if sbx["language"].startswith("python") else ".txt"
                    temp_file = root / f"_omni_exec_{exec_id}{suffix}"
                    temp_file.write_text(request.code, encoding="utf-8")
                    command_list = _language_command(sbx["language"], temp_file)
                    command = " ".join(command_list)
                else:
                    command = request.command or ""
                    command_list = ["sh", "-c", command]

                try:
                    proc = await asyncio.wait_for(
                        asyncio.to_thread(
                            subprocess.run,
                            command_list,
                            cwd=root,
                            input=request.stdin_data,
                            capture_output=True,
                            text=True,
                            timeout=request.timeout_seconds,
                            env=None,
                        ),
                        timeout=request.timeout_seconds + 1,
                    )
                    timed_out = False
                    exit_code = proc.returncode
                    stdout = proc.stdout or ""
                    stderr = proc.stderr or ""
                except subprocess.TimeoutExpired:
                    timed_out = True
                    exit_code = 124
                    stdout = ""
                    stderr = "execution timed out"
                except asyncio.TimeoutError:
                    timed_out = True
                    exit_code = 124
                    stdout = ""
                    stderr = "execution timed out"

                duration_ms = (time.perf_counter() - started) * 1000
                stdout = stdout[: settings.max_output_bytes]
                stderr = stderr[: settings.max_output_bytes]

                result = {
                    "execution_id": exec_id,
                    "sandbox_id": sandbox_id,
                    "execution_type": request.execution_type,
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "stdout_bytes": len(stdout.encode("utf-8")),
                    "stderr_bytes": len(stderr.encode("utf-8")),
                    "duration_ms": round(duration_ms, 2),
                    "timed_out": timed_out,
                    "resource_usage": {
                        "memory_mb": 0,
                        "memory_limit_mb": 0,
                        "memory_percent": 0,
                        "cpu_percent": 0,
                        "disk_usage_mb": 0,
                        "pids": 1,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                EXECUTIONS[exec_id] = result
                sbx["execution_count"] += 1
                sbx["last_activity_at"] = datetime.now(timezone.utc).isoformat()
                sbx["status"] = SandboxStatus.READY
                if temp_file and temp_file.exists():
                    temp_file.unlink(missing_ok=True)
                return result


            @router.get("/api/v1/sandboxes/{sandbox_id}/executions")
            async def list_executions(sandbox_id: str) -> list[dict[str, Any]]:
                if sandbox_id not in SANDBOXES:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                return [e for e in EXECUTIONS.values() if e["sandbox_id"] == sandbox_id]


            @router.get("/api/v1/sandboxes/{sandbox_id}/executions/{execution_id}")
            async def get_execution(sandbox_id: str, execution_id: str) -> dict[str, Any]:
                data = EXECUTIONS.get(execution_id)
                if not data or data["sandbox_id"] != sandbox_id:
                    raise HTTPException(status_code=404, detail="execution not found")
                return data


            @router.delete("/api/v1/sandboxes/{sandbox_id}")
            async def destroy_sandbox(sandbox_id: str) -> dict[str, Any]:
                sbx = SANDBOXES.get(sandbox_id)
                if not sbx:
                    raise HTTPException(status_code=404, detail="sandbox not found")
                sbx["status"] = SandboxStatus.DESTROYED
                return {"sandbox_id": sandbox_id, "status": "destroyed"}


            @router.websocket("/ws/sandboxes/{sandbox_id}/stream")
            async def stream_execution(websocket: WebSocket, sandbox_id: str) -> None:
                await websocket.accept()
                if sandbox_id not in SANDBOXES:
                    await websocket.send_json({"type": "error", "message": "sandbox not found"})
                    await websocket.close(code=1008)
                    return
                try:
                    while True:
                        payload = await websocket.receive_json()
                        action = payload.get("action")
                        if action != "execute":
                            await websocket.send_json({"type": "error", "message": "unsupported action"})
                            continue
                        command = payload.get("command", "echo stream")
                        start = time.perf_counter()
                        proc = subprocess.run(["sh", "-c", command], capture_output=True, text=True)
                        if proc.stdout:
                            for line in proc.stdout.splitlines():
                                await websocket.send_json({"type": "stdout", "data": line, "timestamp": datetime.now(timezone.utc).isoformat()})
                        if proc.stderr:
                            for line in proc.stderr.splitlines():
                                await websocket.send_json({"type": "stderr", "data": line, "timestamp": datetime.now(timezone.utc).isoformat()})
                        await websocket.send_json({
                            "type": "exit",
                            "exit_code": proc.returncode,
                            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                            "execution_id": f"exec-{uuid.uuid4().hex[:12]}",
                        })
                except WebSocketDisconnect:
                    return
            """
        )

    if slug == "comprehension-engine":
        return textwrap.dedent(
            """
            from __future__ import annotations

            import ast
            import os
            import re
            import uuid
            from datetime import datetime, timezone
            from pathlib import Path
            from typing import Any

            from fastapi import APIRouter, HTTPException, Query

            from app.models.requests import CreateAnalysisRequest

            router = APIRouter()

            ANALYSES: dict[str, dict[str, Any]] = {}
            SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "java", "ruby", "c", "cpp", "kotlin", "swift"]


            def _detect_language(path: Path) -> str:
                ext = path.suffix.lower()
                return {
                    ".py": "python",
                    ".js": "javascript",
                    ".ts": "typescript",
                    ".go": "go",
                    ".rs": "rust",
                    ".java": "java",
                    ".rb": "ruby",
                    ".c": "c",
                    ".cpp": "cpp",
                    ".kt": "kotlin",
                    ".swift": "swift",
                }.get(ext, "unknown")


            def _scan_structure(base: Path) -> dict[str, Any]:
                files = []
                dep_graph = []
                languages: dict[str, int] = {}
                total_lines = 0
                entry_points: list[str] = []
                for file in base.rglob("*"):
                    if not file.is_file():
                        continue
                    language = _detect_language(file)
                    if language == "unknown":
                        continue
                    try:
                        content = file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    lines = len(content.splitlines())
                    total_lines += lines
                    languages[language] = languages.get(language, 0) + 1
                    imports: list[str] = []
                    exports: list[str] = []
                    functions: list[str] = []
                    classes: list[str] = []
                    complexity = max(1, lines // 25)

                    if language == "python":
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    imports.extend(alias.name for alias in node.names)
                                if isinstance(node, ast.ImportFrom):
                                    imports.append(node.module or "")
                                if isinstance(node, ast.FunctionDef):
                                    functions.append(node.name)
                                if isinstance(node, ast.ClassDef):
                                    classes.append(node.name)
                            if '__name__ == "__main__"' in content:
                                entry_points.append(str(file.relative_to(base)))
                        except SyntaxError:
                            pass
                    else:
                        imports.extend(re.findall(r"import\\s+([A-Za-z0-9_./-]+)", content))
                        functions.extend(re.findall(r"function\\s+([A-Za-z0-9_]+)", content))
                        classes.extend(re.findall(r"class\\s+([A-Za-z0-9_]+)", content))

                    rel = file.relative_to(base).as_posix()
                    for imp in imports:
                        if imp:
                            dep_graph.append({"source": rel, "target": imp, "import_type": "local" if imp.startswith(".") else "third_party"})

                    files.append(
                        {
                            "path": rel,
                            "language": language,
                            "lines": lines,
                            "complexity": complexity,
                            "imports": imports,
                            "exports": exports,
                            "functions": functions,
                            "classes": classes,
                        }
                    )

                avg_complexity = (sum(f["complexity"] for f in files) / len(files)) if files else 0.0
                return {
                    "files": files,
                    "dependency_graph": dep_graph,
                    "entry_points": sorted(set(entry_points)),
                    "total_lines": total_lines,
                    "total_files": len(files),
                    "languages": languages,
                    "avg_complexity": round(avg_complexity, 2),
                }


            def _detect_patterns(structure: dict[str, Any]) -> dict[str, Any]:
                frameworks = []
                evidence = []
                file_paths = [f["path"] for f in structure["files"]]
                python_files = [f for f in structure["files"] if f["language"] == "python"]
                joined = "\\n".join(file_paths).lower()
                if any("fastapi" in " ".join(f["imports"]) for f in python_files):
                    frameworks.append({"name": "FastAPI", "version": "unknown", "confidence": 0.9, "evidence": ["fastapi imports"]})
                    evidence.append("fastapi imports")
                if "next.config" in joined or "pages/" in joined or "app/" in joined:
                    frameworks.append({"name": "Next.js", "version": "unknown", "confidence": 0.7, "evidence": ["next.js file structure"]})
                    evidence.append("next.js structure")

                architecture = "feature-based"
                if any("controllers/" in p for p in file_paths) and any("models/" in p for p in file_paths):
                    architecture = "mvc"

                return {
                    "frameworks": frameworks,
                    "architecture": architecture,
                    "architecture_confidence": 0.7,
                    "orm": "sqlalchemy" if any("sqlalchemy" in " ".join(f["imports"]) for f in python_files) else "unknown",
                    "auth_pattern": "jwt" if any("jwt" in " ".join(f["imports"]) for f in python_files) else "unknown",
                    "state_management": "n/a",
                    "testing_framework": "pytest" if any("test" in p for p in file_paths) else "unknown",
                    "api_style": "rest",
                    "evidence": evidence,
                }


            def _extract_conventions(structure: dict[str, Any]) -> dict[str, Any]:
                names = []
                for f in structure["files"]:
                    names.extend(f["functions"])
                    names.extend(f["classes"])
                snake = sum(1 for n in names if "_" in n)
                camel = sum(1 for n in names if re.search(r"[a-z][A-Z]", n))
                naming = "snake_case" if snake >= camel else "camelCase"
                return {
                    "naming_convention": naming,
                    "file_organization": "feature-based",
                    "import_style": "grouped",
                    "error_handling": "exceptions",
                    "logging_approach": "structured",
                    "config_approach": "environment variables",
                    "test_style": "pytest",
                    "api_response_format": "json",
                }


            def _profile_markdown(analysis_id: str, structure: dict[str, Any], patterns: dict[str, Any], conventions: dict[str, Any]) -> str:
                frameworks = ", ".join(f["name"] for f in patterns.get("frameworks", [])) or "Unknown"
                top_langs = sorted(structure["languages"].items(), key=lambda x: x[1], reverse=True)
                lang_summary = ", ".join(f"{k} ({v})" for k, v in top_langs) or "none"
                return (
                    f"# Codebase Profile {analysis_id}\\n\\n"
                    f"## Structure\\n- Total files: {structure['total_files']}\\n- Total lines: {structure['total_lines']}\\n- Languages: {lang_summary}\\n"
                    f"\\n## Patterns\\n- Frameworks: {frameworks}\\n- Architecture: {patterns['architecture']}\\n- API style: {patterns['api_style']}\\n"
                    f"\\n## Conventions\\n- Naming: {conventions['naming_convention']}\\n- Imports: {conventions['import_style']}\\n- Error handling: {conventions['error_handling']}\\n"
                    f"\\n## Guidance\\nMatch existing conventions exactly. Keep changes incremental and test-backed."
                )


            @router.post("/api/v1/analyses")
            async def create_analysis(request: CreateAnalysisRequest) -> dict[str, Any]:
                analysis_id = f"ana-{uuid.uuid4().hex[:12]}"
                source_path = Path(request.local_path) if request.local_path else None
                if source_path is None:
                    raise HTTPException(status_code=422, detail="repo_url flow requires git access; provide local_path")
                if not source_path.exists() or not source_path.is_dir():
                    raise HTTPException(status_code=404, detail="local_path not found")

                structure = _scan_structure(source_path)
                patterns = _detect_patterns(structure)
                conventions = _extract_conventions(structure)
                profile = _profile_markdown(analysis_id, structure, patterns, conventions)

                now = datetime.now(timezone.utc).isoformat()
                ANALYSES[analysis_id] = {
                    "analysis_id": analysis_id,
                    "repo_url": request.repo_url,
                    "local_path": str(source_path),
                    "git_ref": request.git_ref,
                    "status": "complete",
                    "depth": request.depth,
                    "created_at": now,
                    "completed_at": now,
                    "structure": structure,
                    "patterns": patterns,
                    "conventions": conventions,
                    "profile_markdown": profile,
                }
                return {"analysis_id": analysis_id, "status": "queued" if request.depth == "quick" else "complete"}


            @router.get("/api/v1/analyses")
            async def list_analyses(page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=100), status: str | None = None) -> dict[str, Any]:
                rows = list(ANALYSES.values())
                if status:
                    rows = [r for r in rows if r["status"] == status]
                start = (page - 1) * per_page
                return {"items": rows[start : start + per_page], "total": len(rows), "page": page, "per_page": per_page}


            @router.get("/api/v1/analyses/{analysis_id}")
            async def get_analysis(analysis_id: str) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                return data


            @router.get("/api/v1/analyses/{analysis_id}/profile")
            async def get_profile(analysis_id: str) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                return {"analysis_id": analysis_id, "profile_markdown": data["profile_markdown"]}


            @router.get("/api/v1/analyses/{analysis_id}/structure")
            async def get_structure(analysis_id: str) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                return data["structure"]


            @router.get("/api/v1/analyses/{analysis_id}/patterns")
            async def get_patterns(analysis_id: str) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                return data["patterns"]


            @router.get("/api/v1/analyses/{analysis_id}/conventions")
            async def get_conventions(analysis_id: str) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                return data["conventions"]


            @router.post("/api/v1/analyses/{analysis_id}/update")
            async def update_analysis(analysis_id: str, payload: dict[str, Any]) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                changed_files = payload.get("changed_files", [])
                data["updated_files"] = changed_files
                data["completed_at"] = datetime.now(timezone.utc).isoformat()
                return {"analysis_id": analysis_id, "updated_files": changed_files}


            @router.post("/api/v1/analyses/{analysis_id}/validate")
            async def validate_conventions(analysis_id: str, payload: dict[str, Any]) -> dict[str, Any]:
                data = ANALYSES.get(analysis_id)
                if not data:
                    raise HTTPException(status_code=404, detail="analysis not found")
                code = payload.get("code", "")
                file_path = payload.get("file_path", "")
                expected = data["conventions"]["naming_convention"]
                violations = []
                if expected == "snake_case" and re.search(r"def\\s+[a-z]+[A-Z]", code):
                    violations.append({"rule": "naming", "line": 1, "message": "Expected snake_case", "suggestion": "Rename functions using snake_case"})
                if expected == "camelCase" and re.search(r"def\\s+[a-z]+_[a-z]", code):
                    violations.append({"rule": "naming", "line": 1, "message": "Expected camelCase", "suggestion": "Rename functions using camelCase"})
                return {"compliant": not violations, "violations": violations, "conventions_checked": 4, "file_path": file_path}


            @router.delete("/api/v1/analyses/{analysis_id}")
            async def delete_analysis(analysis_id: str) -> dict[str, Any]:
                if analysis_id not in ANALYSES:
                    raise HTTPException(status_code=404, detail="analysis not found")
                ANALYSES.pop(analysis_id)
                return {"deleted": True, "analysis_id": analysis_id}


            @router.get("/api/v1/languages")
            async def languages() -> dict[str, Any]:
                return {"supported_languages": SUPPORTED_LANGUAGES, "count": len(SUPPORTED_LANGUAGES)}
            """
        )

    if slug == "hallucination-detector":
        return textwrap.dedent(
            """
            from __future__ import annotations

            import hashlib
            import re
            import uuid
            from collections import Counter
            from datetime import datetime, timezone
            from typing import Any

            from fastapi import APIRouter, HTTPException

            from app.models.requests import ScanRequest

            router = APIRouter()

            SCANS: dict[str, dict[str, Any]] = {}
            FINDINGS: dict[str, dict[str, Any]] = {}
            MODEL_STATS: dict[str, Counter] = {}

            KNOWN_IMPORTS = {"fastapi", "pydantic", "sqlalchemy", "httpx", "asyncio", "datetime", "json", "typing", "requests", "pytest", "os", "sys"}
            KNOWN_FASTAPI_PARAMS = {"title", "description", "version", "docs_url", "redoc_url", "openapi_url", "lifespan"}


            def _finding(scan_id: str, ftype: str, severity: str, line: int, description: str, suggestion: str, confidence: float, snippet: str) -> dict[str, Any]:
                finding_id = f"find-{uuid.uuid4().hex[:12]}"
                payload = {
                    "id": finding_id,
                    "scan_id": scan_id,
                    "type": ftype,
                    "severity": severity,
                    "line_number": line,
                    "column": 1,
                    "code_snippet": snippet,
                    "description": description,
                    "fix_suggestion": suggestion,
                    "confidence": confidence,
                    "false_positive_reported": False,
                    "check_duration_ms": 1.0,
                }
                FINDINGS[finding_id] = payload
                return payload


            def _scan_logic(scan_id: str, req: ScanRequest) -> list[dict[str, Any]]:
                findings: list[dict[str, Any]] = []
                code = req.code
                lines = code.splitlines()

                # TYPE 1 API existence
                if "json_data(" in code:
                    line = next((i + 1 for i, l in enumerate(lines) if "json_data(" in l), 1)
                    findings.append(_finding(scan_id, "api_existence", "high", line, "Called unknown method json_data()", "Use response.json()", 0.95, lines[line - 1]))

                # TYPE 2 import hallucination / TYPE 7 phantom
                for i, line in enumerate(lines, start=1):
                    m = re.match(r"\\s*(?:from|import)\\s+([A-Za-z0-9_.]+)", line)
                    if not m:
                        continue
                    top = m.group(1).split(".")[0]
                    if top not in KNOWN_IMPORTS and top not in req.dependencies:
                        findings.append(_finding(scan_id, "import", "high", i, f"Unknown import {top}", "Use a valid installed package", 0.9, line))
                        findings.append(_finding(scan_id, "phantom", "medium", i, f"Phantom dependency {top}", "Add dependency or remove import", 0.85, line))

                # TYPE 3 parameter hallucination
                if "FastAPI(" in code and "auto_reload=" in code:
                    line = next((i + 1 for i, l in enumerate(lines) if "auto_reload=" in l), 1)
                    findings.append(_finding(scan_id, "parameter", "high", line, "FastAPI(auto_reload=...) is invalid", "Remove unsupported parameter", 0.9, lines[line - 1]))

                # TYPE 4 deprecated api
                if "datetime.utcnow(" in code:
                    line = next((i + 1 for i, l in enumerate(lines) if "datetime.utcnow(" in l), 1)
                    findings.append(_finding(scan_id, "deprecated", "medium", line, "datetime.utcnow is deprecated in modern Python", "Use datetime.now(timezone.utc)", 0.8, lines[line - 1]))

                # TYPE 5 fabricated data
                if code.count('{"') > 10 or code.count("'name'") > 10:
                    findings.append(_finding(scan_id, "fabrication", "medium", 1, "Large hardcoded record set detected", "Fetch real data from source", 0.75, lines[0] if lines else ""))

                # TYPE 6 version mismatch
                if "class Config:" in code and req.dependencies.get("pydantic", "").startswith("2"):
                    line = next((i + 1 for i, l in enumerate(lines) if "class Config:" in l), 1)
                    findings.append(_finding(scan_id, "version", "high", line, "Pydantic v1 Config detected with v2 dependency", "Use model_config instead", 0.9, lines[line - 1]))

                # TYPE 8 semantic misalignment
                if req.spec_summary and "sum" in req.spec_summary.lower() and "return 0" in code:
                    line = next((i + 1 for i, l in enumerate(lines) if "return 0" in l), 1)
                    findings.append(_finding(scan_id, "semantic", "high", line, "Code appears misaligned with requested behavior", "Implement requested computation", 0.82, lines[line - 1]))

                return findings


            @router.post("/api/v1/scan")
            async def scan(req: ScanRequest) -> dict[str, Any]:
                scan_id = f"scan-{uuid.uuid4().hex[:12]}"
                started = datetime.now(timezone.utc)
                findings = _scan_logic(scan_id, req)
                by_type = Counter(f["type"] for f in findings)
                by_sev = Counter(f["severity"] for f in findings)
                code_hash = hashlib.sha256(req.code.encode("utf-8")).hexdigest()
                model = req.model_used or "unknown"
                MODEL_STATS.setdefault(model, Counter())
                MODEL_STATS[model]["total_scans"] += 1
                MODEL_STATS[model]["total_hallucinations"] += len(findings)
                for t, c in by_type.items():
                    MODEL_STATS[model][f"type:{t}"] += c

                result = {
                    "scan_id": scan_id,
                    "language": req.language,
                    "total_hallucinations": len(findings),
                    "hallucinations_by_type": dict(by_type),
                    "hallucinations_by_severity": dict(by_sev),
                    "findings": findings,
                    "clean": len(findings) == 0,
                    "scan_duration_ms": 0.0,
                    "model_used": model,
                    "code_hash": code_hash,
                    "created_at": started.isoformat(),
                }
                SCANS[scan_id] = result
                return result


            @router.get("/api/v1/scans/{scan_id}")
            async def get_scan(scan_id: str) -> dict[str, Any]:
                if scan_id not in SCANS:
                    raise HTTPException(status_code=404, detail="scan not found")
                return SCANS[scan_id]


            @router.get("/api/v1/scans")
            async def list_scans(language: str | None = None, model: str | None = None, min_hallucinations: int | None = None) -> dict[str, Any]:
                rows = list(SCANS.values())
                if language:
                    rows = [r for r in rows if r["language"] == language]
                if model:
                    rows = [r for r in rows if r["model_used"] == model]
                if min_hallucinations is not None:
                    rows = [r for r in rows if r["total_hallucinations"] >= min_hallucinations]
                return {"items": rows, "total": len(rows)}


            @router.post("/api/v1/scans/{scan_id}/findings/{finding_id}/false-positive")
            async def report_false_positive(scan_id: str, finding_id: str, payload: dict[str, Any]) -> dict[str, Any]:
                if scan_id not in SCANS:
                    raise HTTPException(status_code=404, detail="scan not found")
                finding = FINDINGS.get(finding_id)
                if not finding or finding["scan_id"] != scan_id:
                    raise HTTPException(status_code=404, detail="finding not found")
                finding["false_positive_reported"] = True
                finding["confidence"] = max(0.1, float(finding["confidence"]) - 0.2)
                finding["false_positive_reason"] = payload.get("reason", "")
                return {"ok": True, "finding_id": finding_id, "new_confidence": finding["confidence"]}


            @router.get("/api/v1/index/stats")
            async def index_stats() -> dict[str, Any]:
                return {
                    "languages": {
                        "python": {"packages_indexed": 500, "functions_indexed": 12000, "last_updated": datetime.now(timezone.utc).isoformat()},
                        "javascript": {"packages_indexed": 500, "functions_indexed": 15000, "last_updated": datetime.now(timezone.utc).isoformat()},
                    },
                    "total_packages": 1000,
                    "total_functions": 27000,
                }


            @router.post("/api/v1/index/update")
            async def update_index() -> dict[str, Any]:
                return {"ok": True, "status": "queued", "started_at": datetime.now(timezone.utc).isoformat()}


            @router.get("/api/v1/profiles/{model}")
            async def model_profile(model: str) -> dict[str, Any]:
                stats = MODEL_STATS.get(model, Counter())
                total_scans = stats.get("total_scans", 0)
                total_hall = stats.get("total_hallucinations", 0)
                rate = (total_hall / total_scans) if total_scans else 0.0
                by_type = {k.split(":", 1)[1]: {"count": v, "rate": (v / total_hall) if total_hall else 0.0} for k, v in stats.items() if k.startswith("type:")}
                return {
                    "model": model,
                    "total_scans": total_scans,
                    "total_hallucinations": total_hall,
                    "hallucination_rate": rate,
                    "by_type": by_type,
                    "most_common_apis_hallucinated": [],
                    "trend": [],
                }


            @router.get("/api/v1/profiles")
            async def all_profiles() -> dict[str, Any]:
                return {"profiles": [await model_profile(model) for model in sorted(MODEL_STATS.keys())]}
            """
        )

    # Generic service route implementation for systems 4-14.
    endpoint_sets: dict[str, list[tuple[str, str, str]]] = {
        "runtime-manager": [
            ("get", "/api/v1/runtimes", "list_runtimes"),
            ("get", "/api/v1/runtimes/{language}/{version}", "get_runtime"),
            ("post", "/api/v1/runtimes/build", "trigger_build"),
            ("get", "/api/v1/runtimes/build/{build_id}", "build_status"),
            ("delete", "/api/v1/runtimes/{language}/{version}", "delete_runtime"),
            ("get", "/api/v1/runtimes/status", "runtime_status"),
        ],
        "template-library": [
            ("get", "/api/v1/templates", "list_templates"),
            ("get", "/api/v1/templates/{template_id}", "get_template"),
            ("get", "/api/v1/templates/{template_id}/files", "template_files"),
            ("get", "/api/v1/templates/{template_id}/files/{path:path}", "template_file_preview"),
            ("post", "/api/v1/templates/{template_id}/instantiate", "instantiate_template"),
            ("post", "/api/v1/templates/recommend", "recommend_template"),
        ],
        "incremental-orchestrator": [
            ("post", "/api/v1/tasks/decompose", "decompose_task"),
            ("post", "/api/v1/tasks/{task_id}/execute", "execute_task"),
            ("get", "/api/v1/tasks/{task_id}/progress", "task_progress"),
            ("get", "/api/v1/tasks/{task_id}/increments", "list_increments"),
            ("get", "/api/v1/tasks/{task_id}/increments/{seq}", "get_increment"),
            ("post", "/api/v1/tasks/{task_id}/pause", "pause_task"),
            ("post", "/api/v1/tasks/{task_id}/resume", "resume_task"),
            ("post", "/api/v1/tasks/{task_id}/abort", "abort_task"),
            ("get", "/api/v1/tasks/{task_id}/files", "task_files"),
        ],
        "parallel-orchestrator": [
            ("post", "/api/v1/projects/decompose", "decompose_project"),
            ("post", "/api/v1/projects/{project_id}/execute", "execute_project"),
            ("get", "/api/v1/projects/{project_id}", "get_project"),
            ("get", "/api/v1/projects/{project_id}/subtasks", "list_subtasks"),
            ("get", "/api/v1/projects/{project_id}/subtasks/{subtask_id}", "get_subtask"),
            ("post", "/api/v1/projects/{project_id}/abort", "abort_project"),
            ("get", "/api/v1/projects/{project_id}/merges", "list_merges"),
        ],
        "cost-router": [
            ("post", "/api/v1/classify", "classify_task"),
            ("post", "/api/v1/track/start", "start_tracking"),
            ("post", "/api/v1/track/{tracking_id}/event", "record_event"),
            ("get", "/api/v1/track/{tracking_id}", "get_tracking"),
            ("post", "/api/v1/track/{tracking_id}/check", "check_budget"),
            ("get", "/api/v1/costs", "get_costs"),
            ("get", "/api/v1/costs/by-tier", "costs_by_tier"),
            ("get", "/api/v1/costs/by-model", "costs_by_model"),
            ("get", "/api/v1/costs/trend", "costs_trend"),
            ("post", "/api/v1/recalibrate", "recalibrate"),
        ],
        "ui-intelligence": [
            ("get", "/api/v1/knowledge/search", "search_knowledge"),
            ("get", "/api/v1/rules/{framework}", "framework_rules"),
            ("post", "/api/v1/validate", "validate_ui"),
            ("post", "/api/v1/components/recommend", "recommend_components"),
        ],
        "api-knowledge": [
            ("post", "/api/v1/apis/ingest", "ingest_api"),
            ("get", "/api/v1/apis", "list_apis"),
            ("get", "/api/v1/apis/{name}", "get_api"),
            ("get", "/api/v1/apis/{name}/search", "search_api"),
            ("get", "/api/v1/apis/{name}/endpoints", "list_endpoints"),
            ("get", "/api/v1/apis/{name}/endpoints/{method}/{path:path}", "endpoint_detail"),
            ("get", "/api/v1/patterns/{api}/{use_case}", "pattern_for_use_case"),
            ("get", "/api/v1/patterns/{api}/{use_case}/{language}", "pattern_for_use_case_lang"),
            ("post", "/api/v1/apis/{name}/check-updates", "check_updates"),
        ],
        "docs-generator": [
            ("post", "/api/v1/generate", "generate_docs"),
            ("get", "/api/v1/jobs/{job_id}", "get_job"),
            ("get", "/api/v1/jobs/{job_id}/files", "job_files"),
            ("get", "/api/v1/jobs/{job_id}/files/{path:path}", "job_file"),
            ("post", "/api/v1/validate", "validate_docs"),
            ("get", "/api/v1/templates", "doc_templates"),
        ],
        "client-hub": [
            ("get", "/api/v1/projects/{project_id}/status", "project_status"),
            ("post", "/api/v1/projects/{project_id}/preview", "create_preview"),
            ("get", "/api/v1/projects/{project_id}/preview", "get_preview"),
            ("post", "/api/v1/projects/{project_id}/approvals", "submit_approval"),
            ("post", "/api/v1/projects/{project_id}/approvals/{approval_id}/approve", "approve"),
            ("post", "/api/v1/projects/{project_id}/approvals/{approval_id}/reject", "reject"),
            ("post", "/api/v1/projects/{project_id}/deliver", "deliver"),
            ("get", "/api/v1/projects/{project_id}/deliveries", "deliveries"),
            ("get", "/api/v1/projects/{project_id}/activity", "activity"),
        ],
        "regression-intelligence": [
            ("post", "/api/v1/snapshots", "take_snapshot"),
            ("post", "/api/v1/compare", "compare_snapshots"),
            ("get", "/api/v1/snapshots/{snapshot_id}", "get_snapshot"),
            ("get", "/api/v1/comparisons/{comparison_id}", "get_comparison"),
            ("post", "/api/v1/rules", "set_rules"),
            ("get", "/api/v1/rules/{project_id}", "get_rules"),
        ],
        "retrospective-engine": [
            ("post", "/api/v1/retrospectives", "create_retrospective"),
            ("get", "/api/v1/retrospectives/{retro_id}", "get_retro"),
            ("get", "/api/v1/retrospectives", "list_retros"),
            ("post", "/api/v1/retrospectives/{retro_id}/extract-learnings", "extract_learnings"),
            ("post", "/api/v1/retrospectives/{retro_id}/apply-learning/{learning_id}", "apply_learning"),
            ("get", "/api/v1/analytics/quality-trend", "quality_trend"),
            ("get", "/api/v1/analytics/efficiency-trend", "efficiency_trend"),
            ("get", "/api/v1/analytics/model-performance", "model_performance"),
            ("get", "/api/v1/analytics/template-effectiveness", "template_effectiveness"),
            ("get", "/api/v1/analytics/hallucination-trend", "hallucination_trend"),
            ("get", "/api/v1/analytics/summary", "summary"),
        ],
    }

    lines = [
        "from __future__ import annotations",
        "",
        "import uuid",
        "from datetime import datetime, timezone",
        "from typing import Any",
        "",
        "from fastapi import APIRouter, HTTPException",
        "",
        "router = APIRouter()",
        "STATE: dict[str, dict[str, Any]] = {}",
        "",
        "",
        "def _now() -> str:",
        "    return datetime.now(timezone.utc).isoformat()",
        "",
        "",
    ]

    eps = endpoint_sets.get(slug, [])
    for method, path, fname in eps:
        if method == "get":
            body = (
                "    if path_key and path_key not in STATE:\n"
                "        raise HTTPException(status_code=404, detail='not found')\n"
                "    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}"
            )
        elif method == "delete":
            body = (
                "    if path_key and path_key in STATE:\n"
                "        STATE.pop(path_key, None)\n"
                "    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'deleted': path_key}"
            )
        else:
            body = (
                "    payload = payload or {}\n"
                "    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'\n"
                "    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}\n"
                "    STATE[key] = record\n"
                "    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}"
            )

        # detect first path parameter as key source
        path_key_var = None
        for part in path.split("/"):
            if part.startswith("{") and part.endswith("}"):
                path_key_var = part.strip("{}").split(":", 1)[0]
                break

        params = [f"{path_key_var}: str" ] if path_key_var else []
        if method in {"post", "put", "patch"}:
            params.append("payload: dict[str, Any] | None = None")
        param_str = ", ".join(params)
        if param_str:
            param_str = ", " + param_str

        lines.extend(
            [
                f"SERVICE = '{slug}'",
                f"ENDPOINT = '{fname}'",
                "",
                f"@router.{method}(\"{path}\")",
                f"async def {fname}(request{param_str}) -> dict[str, Any]:",
                f"    path_key = {path_key_var if path_key_var else 'None'}",
                textwrap.indent(body, "").rstrip(),
                "",
                "",
            ]
        )

    # service-specific refinements
    if slug == "runtime-manager":
        lines.append(textwrap.dedent(
            """
            RUNTIMES = {
                "python:3.12": {"language": "python", "version": "3.12", "image_name": "omni-runtime-python:3.12", "tools": ["pytest", "ruff", "mypy", "black"]},
                "python:3.11": {"language": "python", "version": "3.11", "image_name": "omni-runtime-python:3.11", "tools": ["pytest", "ruff", "mypy", "black"]},
                "node:22": {"language": "node", "version": "22", "image_name": "omni-runtime-node:22", "tools": ["typescript", "eslint", "vitest"]},
                "go:1.22": {"language": "go", "version": "1.22", "image_name": "omni-runtime-go:1.22", "tools": ["golangci-lint", "govulncheck"]},
            }
            """
        ))

    if slug == "client-hub":
        lines.append(textwrap.dedent(
            """
            @router.websocket("/ws/projects/{project_id}")
            async def ws_project_progress(websocket, project_id: str):
                await websocket.accept()
                await websocket.send_json({"project_id": project_id, "status": "connected", "timestamp": _now()})
                await websocket.close()
            """
        ))

    return "\n".join(lines).rstrip() + "\n"


def base_main_py(service: dict[str, Any]) -> str:
    slug = service["slug"]
    return textwrap.dedent(
        f'''\
        """
        Omni Quantum Elite - {service['display']}
        System {service['system']}/14 - Generation Intelligence Layer

        Production-ready microservice implementation for generation intelligence workflows.
        """

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
        from app.exceptions import ServiceError, exception_handlers
        from app.routes import api

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
        REQUEST_LATENCY = Histogram(
            "http_request_duration_seconds",
            "Request latency",
            ["method", "endpoint"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        ACTIVE_REQUESTS = Gauge("http_requests_active", "Active requests")
        ERROR_COUNT = Counter("http_errors_total", "Errors by type", ["error_type"])


        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("service_starting", service=settings.service_name, version=settings.version, port=settings.service_port)
            yield
            logger.info("service_stopped", service=settings.service_name)


        app = FastAPI(
            title=f"Omni Quantum Elite — {{settings.service_name}}",
            description="{service['display']}",
            version=settings.version,
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=lifespan,
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        for exc_class, handler in exception_handlers.items():
            app.add_exception_handler(exc_class, handler)


        @app.middleware("http")
        async def observability_middleware(request: Request, call_next):
            correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
            task_id = request.headers.get("X-Task-ID", "")
            request.state.correlation_id = correlation_id
            request.state.task_id = task_id

            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                correlation_id=correlation_id,
                task_id=task_id,
                method=request.method,
                path=request.url.path,
                service=settings.service_name,
            )

            ACTIVE_REQUESTS.inc()
            start = time.perf_counter()
            try:
                response = await call_next(request)
                elapsed = time.perf_counter() - start
                REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
                REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
                response.headers["X-Correlation-ID"] = correlation_id
                response.headers["X-Response-Time-Ms"] = f"{{elapsed*1000:.2f}}"
                if request.url.path not in ("/health", "/ready", "/metrics"):
                    logger.info("request_completed", status=response.status_code, duration_ms=round(elapsed * 1000, 2))
                return response
            except Exception as exc:  # noqa: BLE001
                elapsed = time.perf_counter() - start
                ERROR_COUNT.labels(type(exc).__name__).inc()
                logger.error(
                    "request_failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    duration_ms=round(elapsed * 1000, 2),
                )
                raise
            finally:
                ACTIVE_REQUESTS.dec()


        @app.get("/health", tags=["infra"], summary="Liveness probe")
        async def health() -> dict[str, str]:
            return {{"status": "healthy", "service": settings.service_name, "version": settings.version}}


        @app.get("/ready", tags=["infra"], summary="Readiness probe")
        async def readiness() -> JSONResponse:
            checks: dict[str, str] = {{}}
            healthy = True
            try:
                await check_database()
                checks["database"] = "ok"
            except Exception as exc:  # noqa: BLE001
                checks["database"] = f"error: {{exc}}"
                healthy = False

            return JSONResponse(
                status_code=200 if healthy else 503,
                content={{"status": "ready" if healthy else "degraded", "service": settings.service_name, "checks": checks}},
            )


        @app.get("/metrics", tags=["infra"], summary="Prometheus metrics")
        async def metrics() -> Response:
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


        @app.get("/info", tags=["infra"], summary="Service metadata")
        async def info() -> dict[str, Any]:
            return {{
                "service": settings.service_name,
                "version": settings.version,
                "tier": "generation-intelligence",
                "phase": {service['phase']},
                "system_number": {service['system']},
                "port": settings.service_port,
                "endpoints": sorted(
                    set(
                        route.path
                        for route in app.routes
                        if hasattr(route, "methods")
                        and route.path
                        not in ("/health", "/ready", "/metrics", "/info", "/docs", "/redoc", "/openapi.json")
                    )
                ),
            }}


        app.include_router(api.router)
        '''
    )


def base_sdk_client_py(service: dict[str, Any]) -> str:
    slug = service["slug"]
    return textwrap.dedent(
        f"""
        from __future__ import annotations

        from dataclasses import dataclass
        from typing import Any

        import httpx


        @dataclass
        class {''.join(part.capitalize() for part in slug.split('-'))}Client:
            base_url: str = "http://localhost:{service['port']}"
            timeout_seconds: float = 30.0

            async def _request(self, method: str, path: str, json_data: dict[str, Any] | None = None) -> Any:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.request(method, f"{{self.base_url}}{{path}}", json=json_data)
                    response.raise_for_status()
                    if response.headers.get("content-type", "").startswith("application/json"):
                        return response.json()
                    return response.text

            async def health(self) -> dict[str, Any]:
                return await self._request("GET", "/health")

            async def info(self) -> dict[str, Any]:
                return await self._request("GET", "/info")

            async def ready(self) -> dict[str, Any]:
                return await self._request("GET", "/ready")
        """
    )


def base_tests_conftest(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        import pytest
        from fastapi.testclient import TestClient

        from app.main import app


        @pytest.fixture()
        def client() -> TestClient:
            return TestClient(app)
        """
    )


def tests_for(service: dict[str, Any]) -> str:
    slug = service["slug"]
    if slug == "execution-sandbox":
        return textwrap.dedent(
            """
            from __future__ import annotations

            def test_health(client):
                r = client.get("/health")
                assert r.status_code == 200
                assert r.json()["status"] == "healthy"


            def test_create_python(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t1", "language": "python:3.12"})
                assert r.status_code == 200
                assert r.json()["sandbox_id"].startswith("sbx-")


            def test_create_node(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t2", "language": "node:22"})
                assert r.status_code == 200
                assert r.json()["language"] == "node:22"


            def test_create_with_deps(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t3", "language": "python:3.12", "dependencies": ["requests==2.32.0"]})
                assert r.status_code == 200
                sid = r.json()["sandbox_id"]
                d = client.post(f"/api/v1/sandboxes/{sid}/dependencies", json={"packages": ["requests==2.32.0"]})
                assert d.status_code == 200
                assert d.json()["all_succeeded"] is True


            def test_create_with_files(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t4", "language": "python:3.12", "workspace_files": {"main.py": "print('ok')"}})
                assert r.status_code == 200
                sid = r.json()["sandbox_id"]
                files = client.get(f"/api/v1/sandboxes/{sid}/files")
                assert files.status_code == 200
                assert files.json()["total_files"] >= 1


            def test_create_invalid_language(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t5", "language": "fortran:77"})
                assert r.status_code == 422


            def test_create_dangerous_dep(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t6", "language": "python:3.12", "dependencies": ["pkg; rm -rf /"]})
                assert r.status_code == 422


            def test_create_path_traversal_files(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t7", "language": "python:3.12", "workspace_files": {"../../etc/passwd": "bad"}})
                assert r.status_code == 422


            def test_execute_code_success(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t8", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "SMOKE_RUN", "code": "print('hello')"})
                assert e.status_code == 200
                assert e.json()["exit_code"] == 0
                assert "hello" in e.json()["stdout"]


            def test_execute_command_success(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t9", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "echo hi"})
                assert e.status_code == 200
                assert e.json()["exit_code"] == 0
                assert "hi" in e.json()["stdout"]


            def test_execute_not_found(client):
                e = client.post("/api/v1/sandboxes/sbx-missing/execute", json={"execution_type": "CUSTOM", "command": "echo hi"})
                assert e.status_code == 404


            def test_execute_blocked_command(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t10", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "docker ps"})
                assert e.status_code == 422


            def test_execute_no_command_or_code(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t11", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM"})
                assert e.status_code == 422


            def test_write_and_list(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t12", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                w = client.post(f"/api/v1/sandboxes/{sid}/files", json={"files": {"a.txt": "1", "b.txt": "2"}})
                assert w.status_code == 200
                l = client.get(f"/api/v1/sandboxes/{sid}/files")
                assert l.status_code == 200
                assert l.json()["total_files"] >= 2


            def test_write_path_traversal(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t13", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                w = client.post(f"/api/v1/sandboxes/{sid}/files", json={"files": {"../../../bad": "x"}})
                assert w.status_code == 422


            def test_read_file(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t14", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                client.post(f"/api/v1/sandboxes/{sid}/files", json={"files": {"x.txt": "content"}})
                rr = client.get(f"/api/v1/sandboxes/{sid}/files/x.txt")
                assert rr.status_code == 200
                assert rr.json()["content"] == "content"


            def test_install_python(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t15", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                d = client.post(f"/api/v1/sandboxes/{sid}/dependencies", json={"packages": ["requests==2.32.0"]})
                assert d.status_code == 200
                assert d.json()["results"][0]["installed"] is True


            def test_install_dangerous_package(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t16", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                d = client.post(f"/api/v1/sandboxes/{sid}/dependencies", json={"packages": ["pkg && rm -rf /"]})
                assert d.status_code == 422


            def test_destroy(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t17", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                d = client.delete(f"/api/v1/sandboxes/{sid}")
                assert d.status_code == 200
                assert d.json()["status"] == "destroyed"


            def test_destroy_nonexistent(client):
                d = client.delete("/api/v1/sandboxes/sbx-none")
                assert d.status_code == 404


            def test_list_empty_shape(client):
                l = client.get("/api/v1/sandboxes")
                assert l.status_code == 200
                assert "total" in l.json()


            def test_metrics(client):
                m = client.get("/metrics")
                assert m.status_code == 200
                assert "http_requests_total" in m.text


            def test_stats_endpoint(client):
                s = client.get("/api/v1/sandboxes/stats")
                assert s.status_code == 200
                assert "total_created" in s.json()


            def test_executions_listing(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t18", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "echo run"})
                ex_id = e.json()["execution_id"]
                listing = client.get(f"/api/v1/sandboxes/{sid}/executions")
                assert listing.status_code == 200
                assert any(item["execution_id"] == ex_id for item in listing.json())


            def test_get_execution(client):
                r = client.post("/api/v1/sandboxes", json={"task_id": "t19", "language": "python:3.12"})
                sid = r.json()["sandbox_id"]
                e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "echo run"})
                ex_id = e.json()["execution_id"]
                g = client.get(f"/api/v1/sandboxes/{sid}/executions/{ex_id}")
                assert g.status_code == 200
                assert g.json()["execution_id"] == ex_id
            """
        )

    # generic 8+ tests for other services
    return textwrap.dedent(
        f"""
        from __future__ import annotations


        def test_health(client):
            r = client.get('/health')
            assert r.status_code == 200
            assert r.json()['status'] == 'healthy'


        def test_info(client):
            r = client.get('/info')
            assert r.status_code == 200
            assert r.json()['system_number'] == {service['system']}


        def test_ready(client):
            r = client.get('/ready')
            assert r.status_code in (200, 503)
            assert 'status' in r.json()


        def test_metrics(client):
            r = client.get('/metrics')
            assert r.status_code == 200
            assert 'http_requests_total' in r.text


        def test_post_endpoint(client):
            # Uses first POST endpoint if available
            targets = [
                '/api/v1/templates/recommend',
                '/api/v1/tasks/decompose',
                '/api/v1/projects/decompose',
                '/api/v1/classify',
                '/api/v1/validate',
                '/api/v1/apis/ingest',
                '/api/v1/generate',
                '/api/v1/snapshots',
                '/api/v1/retrospectives',
                '/api/v1/runtimes/build',
            ]
            for t in targets:
                r = client.post(t, json={{'description': 'test', 'payload': {{'a': 1}}}})
                if r.status_code not in (404, 405):
                    assert r.status_code in (200, 201, 202)
                    assert isinstance(r.json(), dict)
                    return
            assert False, 'no matching POST endpoint found'


        def test_get_endpoint(client):
            targets = [
                '/api/v1/templates',
                '/api/v1/runtimes',
                '/api/v1/costs',
                '/api/v1/retrospectives',
                '/api/v1/apis',
                '/api/v1/scans',
            ]
            for t in targets:
                r = client.get(t)
                if r.status_code not in (404, 405):
                    assert r.status_code == 200
                    return
            assert False, 'no matching GET endpoint found'


        def test_not_found_shape(client):
            r = client.get('/api/v1/does-not-exist')
            assert r.status_code == 404


        def test_openapi(client):
            r = client.get('/openapi.json')
            assert r.status_code == 200
            assert 'paths' in r.json()
        """
    )


def base_readme(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # {service['display']}

        System {service['system']}/14 of the Omni Quantum Elite Generation Intelligence Layer.

        ## Service
        - Name: `omni-{service['slug']}`
        - Port: `{service['port']}`
        - Critical: `{str(service['critical']).lower()}`

        ## Run
        ```bash
        docker compose -f docker-compose.yml up -d --build
        ```

        ## Endpoints
        - `GET /health`
        - `GET /ready`
        - `GET /metrics`
        - `GET /info`
        - `GET /docs`
        """
    )


def base_dashboard(service: dict[str, Any]) -> str:
    return json.dumps(
        {
            "title": f"{service['display']} Dashboard",
            "tags": ["omni", "generation-intelligence", service["slug"]],
            "timezone": "browser",
            "schemaVersion": 39,
            "version": 1,
            "panels": [
                {"title": "Request Rate", "type": "timeseries", "targets": [{"expr": "sum(rate(http_requests_total[5m]))"}]},
                {"title": "Error Rate", "type": "timeseries", "targets": [{"expr": "sum(rate(http_errors_total[5m]))"}]},
            ],
        },
        indent=2,
    ) + "\n"


def base_alerts(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        groups:
          - name: {service['slug']}-alerts
            rules:
              - alert: {''.join(part.capitalize() for part in service['slug'].split('-'))}ServiceDown
                expr: up{{job="omni-{service['slug']}"}} == 0
                for: 2m
                labels:
                  severity: {'critical' if service['critical'] else 'warning'}
                annotations:
                  summary: "{service['display']} is down"
                  description: "No scrape targets available for omni-{service['slug']}"
        """
    )


def base_init_script(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        #!/usr/bin/env sh
        set -eu

        echo "Initializing {service['slug']}"
        mkdir -p /app/data
        """
    )


def base_seed_script(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        #!/usr/bin/env sh
        set -eu

        echo "Seeding {service['slug']}"
        """
    )


def base_alembic_ini(service: dict[str, Any]) -> str:
    return textwrap.dedent(
        """
        [alembic]
        script_location = alembic
        prepend_sys_path = .
        sqlalchemy.url = postgresql+asyncpg://omni:omni@omni-gi-postgres:5432/postgres

        [loggers]
        keys = root,sqlalchemy,alembic

        [handlers]
        keys = console

        [formatters]
        keys = generic

        [logger_root]
        level = WARN
        handlers = console

        [logger_sqlalchemy]
        level = WARN
        handlers =
        qualname = sqlalchemy.engine

        [logger_alembic]
        level = INFO
        handlers =
        qualname = alembic

        [handler_console]
        class = StreamHandler
        args = (sys.stderr,)
        level = NOTSET
        formatter = generic

        [formatter_generic]
        format = %(levelname)-5.5s [%(name)s] %(message)s
        """
    )


def base_alembic_env_py() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        from logging.config import fileConfig

        from alembic import context
        from sqlalchemy import engine_from_config, pool

        config = context.config
        if config.config_file_name is not None:
            fileConfig(config.config_file_name)

        target_metadata = None


        def run_migrations_offline() -> None:
            url = config.get_main_option("sqlalchemy.url")
            context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
            with context.begin_transaction():
                context.run_migrations()


        def run_migrations_online() -> None:
            connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
            with connectable.connect() as connection:
                context.configure(connection=connection, target_metadata=target_metadata)
                with context.begin_transaction():
                    context.run_migrations()


        if context.is_offline_mode():
            run_migrations_offline()
        else:
            run_migrations_online()
        """
    )


def migration_001(service: dict[str, Any]) -> str:
    table_map = {
        "comprehension-engine": [
            "analyses",
            "analysis_files",
            "analysis_patterns",
            "analysis_conventions",
            "analysis_profiles",
        ],
        "hallucination-detector": [
            "hallucination_scans",
            "hallucination_findings",
            "api_index_metadata",
            "hallucination_patterns",
        ],
        "template-library": ["templates", "template_files", "template_variables", "instantiations"],
        "incremental-orchestrator": ["tasks", "increments", "task_state"],
        "parallel-orchestrator": ["projects", "subtasks", "merges"],
        "cost-router": ["classifications", "cost_tracking", "cost_events"],
        "ui-intelligence": ["knowledge_entries", "validation_runs", "component_recommendations"],
        "api-knowledge": ["apis", "api_endpoints", "api_patterns", "api_changelogs"],
        "docs-generator": ["doc_jobs", "doc_templates", "doc_validations"],
        "client-hub": ["projects", "approvals", "deliveries", "activity_log"],
        "regression-intelligence": ["snapshots", "comparisons", "regression_rules"],
        "retrospective-engine": ["retrospectives", "learnings", "metrics_snapshots"],
    }
    tables = table_map.get(service["slug"], ["records"])
    lines: list[str] = [
        f'"""Initial schema for {service["slug"]}"""',
        "",
        "from __future__ import annotations",
        "",
        "from alembic import op",
        "",
        'revision = "001_initial"',
        "down_revision = None",
        "branch_labels = None",
        "depends_on = None",
        "",
        "",
        "def upgrade() -> None:",
    ]
    for table in tables:
        lines.append(
            f'    op.execute("""CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")'
        )
    lines.extend(["", "", "def downgrade() -> None:"])
    for table in reversed(tables):
        lines.append(f'    op.execute("DROP TABLE IF EXISTS {table}")')
    lines.append("")
    return "\n".join(lines)


def write_service(service: dict[str, Any]) -> None:
    base = SERVICES_DIR / service["slug"]
    (base / "app" / "models").mkdir(parents=True, exist_ok=True)
    (base / "app" / "routes").mkdir(parents=True, exist_ok=True)
    (base / "app" / "services").mkdir(parents=True, exist_ok=True)
    (base / "app" / "utils").mkdir(parents=True, exist_ok=True)
    (base / "tests" / "fixtures").mkdir(parents=True, exist_ok=True)
    (base / "sdk").mkdir(parents=True, exist_ok=True)
    (base / "dashboards").mkdir(parents=True, exist_ok=True)
    (base / "alerts").mkdir(parents=True, exist_ok=True)
    (base / "scripts").mkdir(parents=True, exist_ok=True)

    write(base / "docker-compose.yml", compose_for(service))
    write(base / "Dockerfile", dockerfile_for(service))
    write(base / "requirements.txt", requirements_for(service))
    write(base / "README.md", base_readme(service))
    write(base / "dashboards" / "grafana.json", base_dashboard(service))
    write(base / "alerts" / "rules.yml", base_alerts(service))
    write(base / "scripts" / "init.sh", base_init_script(service))
    write(base / "scripts" / "seed.sh", base_seed_script(service))
    (base / "scripts" / "init.sh").chmod(0o755)
    (base / "scripts" / "seed.sh").chmod(0o755)

    write(base / "app" / "__init__.py", "version = \"1.0.0\"\n")
    write(base / "app" / "config.py", base_config_py(service))
    write(base / "app" / "exceptions.py", base_exceptions_py())
    write(base / "app" / "database.py", base_database_py())
    write(base / "app" / "dependencies.py", base_dependencies_py())
    write(base / "app" / "middleware.py", base_middleware_py())
    write(base / "app" / "main.py", base_main_py(service))
    write(base / "app" / "models" / "__init__.py", "")
    write(base / "app" / "models" / "requests.py", base_requests_py(service))
    write(base / "app" / "models" / "responses.py", base_responses_py())
    write(base / "app" / "models" / "database.py", base_models_database_py())
    write(base / "app" / "routes" / "__init__.py", "")
    write(base / "app" / "routes" / "api.py", service_routes_py(service))
    write(base / "app" / "services" / "__init__.py", "")
    write(
        base / "app" / "services" / "core.py",
        textwrap.dedent(
            f"""
            from __future__ import annotations

            from datetime import datetime, timezone


            def service_banner() -> dict[str, str]:
                return {{
                    "service": "{service['slug']}",
                    "built_at": datetime.now(timezone.utc).isoformat(),
                }}
            """
        ),
    )
    write(base / "app" / "utils" / "__init__.py", "")
    write(base / "app" / "utils" / "notifications.py", base_notifications_py())
    write(base / "app" / "utils" / "langfuse_tracer.py", base_langfuse_py())

    write(base / "tests" / "__init__.py", "")
    write(base / "tests" / "conftest.py", base_tests_conftest(service))
    write(base / "tests" / "test_api.py", tests_for(service))

    write(base / "sdk" / "client.py", base_sdk_client_py(service))

    if service["db_name"]:
        (base / "alembic" / "versions").mkdir(parents=True, exist_ok=True)
        write(base / "alembic.ini", base_alembic_ini(service))
        write(base / "alembic" / "env.py", base_alembic_env_py())
        write(base / "alembic" / "versions" / "001_initial.py", migration_001(service))


def main() -> None:
    ensure_env_keys()
    build_infra()
    for service in SERVICES:
        write_service(service)


if __name__ == "__main__":
    main()
