# ══════════════════════════════════════════════════════════════════════════════════════════════
# MEDIUM PRIORITY SYSTEMS — PART 2
# OMNI QUANTUM ELITE — ULTIMATE EDITION
# Systems 22-25: Omi Command Center, Knowledge Base, Analytics Engine, Scheduling
# ══════════════════════════════════════════════════════════════════════════════════════════════

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 22: OMI COMMAND CENTER — WEARABLE INTEGRATION HUB
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               OMI COMMAND CENTER ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  OMI DEVICE                      BRIDGE LAYER                       OMNI QUANTUM CORE       │
│  ──────────                      ────────────                       ───────────────         │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🎙️ Audio Stream  │          │                               │  │  🧠 LiteLLM       │      │
│  │  • Voice capture  │─────────▶│     OMI BRIDGE API            │─▶│  • Transcription  │      │
│  │  • Wake word      │  BLE/    │                               │  │  • Summarization  │      │
│  │  • Noise cancel   │  WiFi    │  ┌─────────────────────────┐ │  │  • Intent detect  │      │
│  └──────────────────┘          │  │ WebSocket Server         │ │  └──────────────────┘      │
│                                │  │ • Real-time audio        │ │                            │
│  ┌──────────────────┐          │  │ • Event streaming        │ │  ┌──────────────────┐      │
│  │  📱 Mobile App    │          │  │ • Heartbeat monitoring   │ │  │  📋 Plane          │      │
│  │  • Companion app  │─────────▶│  └─────────────────────────┘ │─▶│  • Create tasks   │      │
│  │  • Settings       │  HTTP    │                               │  │  • Update status  │      │
│  │  • History        │          │  ┌─────────────────────────┐ │  └──────────────────┘      │
│  └──────────────────┘          │  │ REST API                 │ │                            │
│                                │  │ • /conversations          │ │  ┌──────────────────┐      │
│  ┌──────────────────┐          │  │ • /memories               │ │  │  💬 Mattermost     │      │
│  │  📡 Sensors       │          │  │ • /actions                │ │─▶│  • Voice notes    │      │
│  │  • Accelerometer  │─────────▶│  │ • /plugins               │ │  │  • Reminders      │      │
│  │  • Gyroscope      │          │  └─────────────────────────┘ │  │  • Alerts          │      │
│  │  • Heart rate     │          │                               │  └──────────────────┘      │
│  └──────────────────┘          │  ┌─────────────────────────┐ │                            │
│                                │  │ PLUGIN ENGINE            │ │  ┌──────────────────┐      │
│                                │  │ • Custom actions          │ │  │  📊 Analytics      │      │
│                                │  │ • Webhook triggers        │ │─▶│  • Activity logs  │      │
│                                │  │ • n8n integration         │ │  │  • Usage metrics  │      │
│                                │  └─────────────────────────┘ │  │  • Patterns        │      │
│                                └───────────────────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.omi.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # OMI COMMAND CENTER — Wearable Integration Bridge
  # ═══════════════════════════════════════════════════════════════════════════
  omi-bridge:
    build:
      context: ./build/omi-bridge
      dockerfile: Dockerfile
    container_name: omni-quantum-omi-bridge
    ports:
      - "3200:8000"     # REST API
      - "3201:8001"     # WebSocket
    environment:
      # ── Server ──
      HOST: "0.0.0.0"
      PORT: 8000
      WS_PORT: 8001
      ENV: "production"
      LOG_LEVEL: "info"

      # ── Database ──
      DATABASE_URL: "postgresql://omi:${OMI_DB_PASSWORD}@postgres:5432/omi"
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/7"

      # ── LLM (via Token Infinity) ──
      LITELLM_BASE_URL: "http://litellm:4000/v1"
      LITELLM_API_KEY: "${LITELLM_API_KEY}"
      TRANSCRIPTION_MODEL: "litellm/groq/whisper-large-v3"
      SUMMARY_MODEL: "litellm/ollama/llama3.2"
      INTENT_MODEL: "litellm/ollama/llama3.2"

      # ── Speech-to-Text ──
      STT_PROVIDER: "local"
      WHISPER_MODEL: "base"

      # ── Integrations ──
      MATTERMOST_URL: "http://mattermost:8065"
      MATTERMOST_TOKEN: "${MATTERMOST_OMI_BOT_TOKEN}"
      N8N_WEBHOOK_BASE: "http://n8n:5678/webhook"
      PLANE_API_URL: "http://plane-api:8000"
      PLANE_API_KEY: "${PLANE_API_KEY}"

      # ── Storage ──
      MINIO_ENDPOINT: "minio:9000"
      MINIO_ACCESS_KEY: "${MINIO_ROOT_USER}"
      MINIO_SECRET_KEY: "${MINIO_ROOT_PASSWORD}"
      MINIO_BUCKET: "uploads"

      # ── Security ──
      JWT_SECRET: "${OMI_JWT_SECRET}"
      API_KEY: "${OMI_API_KEY}"
      CORS_ORIGINS: "*"

      # ── Observability ──
      LANGFUSE_PUBLIC_KEY: "${LANGFUSE_PUBLIC_KEY}"
      LANGFUSE_SECRET_KEY: "${LANGFUSE_SECRET_KEY}"
      LANGFUSE_HOST: "http://langfuse:3000"
    volumes:
      - omi_data:/app/data
      - ./config/omi/plugins:/app/plugins:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      litellm:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    labels:
      - "omni.quantum.component=omi-bridge"
      - "omni.quantum.tier=wearable"
      - "omni.quantum.system=22"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  omi_data:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## BUILD DOCKERFILE

```dockerfile
# build/omi-bridge/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

## PYTHON SDK — OMI CLIENT

```python
# sdk/omi_client.py
# ═══════════════════════════════════════════════════════════════════════════════
# OMI COMMAND CENTER SDK — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

"""
Omi wearable integration client. Manages conversations, memories,
voice commands, and real-time audio streaming.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional

import aiohttp

logger = logging.getLogger("omni.quantum.omi")


class ConversationStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    PROCESSING = "processing"


@dataclass
class Memory:
    id: str
    content: str
    source: str  # "voice", "text", "sensor"
    created_at: datetime
    tags: list[str] = field(default_factory=list)
    sentiment: Optional[str] = None
    action_items: list[str] = field(default_factory=list)


@dataclass
class VoiceCommand:
    transcript: str
    intent: str
    confidence: float
    parameters: dict = field(default_factory=dict)
    action_taken: Optional[str] = None


class OmiClient:
    """Async client for Omi Command Center."""

    def __init__(
        self,
        api_url: str = "http://omi-bridge:8000",
        ws_url: str = "ws://omi-bridge:8001",
        api_key: str = "",
    ):
        self.api_url = api_url.rstrip("/")
        self.ws_url = ws_url.rstrip("/")
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._session

    async def get_memories(
        self,
        limit: int = 50,
        offset: int = 0,
        tags: Optional[list[str]] = None,
        since: Optional[datetime] = None,
    ) -> list[Memory]:
        """Retrieve stored memories with filtering."""
        session = await self._get_session()
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if tags:
            params["tags"] = ",".join(tags)
        if since:
            params["since"] = since.isoformat()
        async with session.get(
            f"{self.api_url}/api/v1/memories", params=params
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return [
                Memory(
                    id=m["id"],
                    content=m["content"],
                    source=m["source"],
                    created_at=datetime.fromisoformat(m["created_at"]),
                    tags=m.get("tags", []),
                    sentiment=m.get("sentiment"),
                    action_items=m.get("action_items", []),
                )
                for m in data.get("memories", [])
            ]

    async def create_memory(
        self,
        content: str,
        source: str = "text",
        tags: Optional[list[str]] = None,
    ) -> Memory:
        """Create a new memory entry."""
        session = await self._get_session()
        payload = {"content": content, "source": source, "tags": tags or []}
        async with session.post(
            f"{self.api_url}/api/v1/memories", json=payload
        ) as resp:
            resp.raise_for_status()
            m = await resp.json()
            return Memory(
                id=m["id"],
                content=m["content"],
                source=m["source"],
                created_at=datetime.fromisoformat(m["created_at"]),
                tags=m.get("tags", []),
            )

    async def send_voice_command(self, audio_data: bytes) -> VoiceCommand:
        """Send audio for transcription and intent detection."""
        session = await self._get_session()
        form = aiohttp.FormData()
        form.add_field("audio", audio_data, content_type="audio/wav")
        async with session.post(
            f"{self.api_url}/api/v1/voice/command", data=form
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return VoiceCommand(
                transcript=data["transcript"],
                intent=data["intent"],
                confidence=data["confidence"],
                parameters=data.get("parameters", {}),
                action_taken=data.get("action_taken"),
            )

    async def stream_events(
        self, callback: Callable[[dict], None]
    ) -> None:
        """Connect to WebSocket for real-time events."""
        session = await self._get_session()
        async with session.ws_connect(
            f"{self.ws_url}/ws/events",
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    event = json.loads(msg.data)
                    callback(event)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break

    async def get_device_status(self) -> dict:
        """Get connected Omi device status."""
        session = await self._get_session()
        async with session.get(f"{self.api_url}/api/v1/device/status") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def trigger_action(self, action: str, params: Optional[dict] = None) -> dict:
        """Trigger a registered action/plugin."""
        session = await self._get_session()
        payload = {"action": action, "params": params or {}}
        async with session.post(
            f"{self.api_url}/api/v1/actions/trigger", json=payload
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-omi.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 22: OMI COMMAND CENTER — WEARABLE INTEGRATION"

ensure_dir "${DATA_ROOT}/omi"
ensure_dir "${CONFIG_ROOT}/omi/plugins"
ensure_dir "${BUILD_ROOT}/omi-bridge"

ensure_secret "OMI_DB_PASSWORD" 32
ensure_secret "OMI_JWT_SECRET" 64
ensure_secret "OMI_API_KEY" 48

create_postgres_db "omi" "omi" "${OMI_DB_PASSWORD}"

# Create sample plugin
cat > "${CONFIG_ROOT}/omi/plugins/task-creator.json" << 'EOF'
{
  "name": "Task Creator",
  "description": "Creates Plane tasks from voice commands",
  "trigger": "intent:create_task",
  "action": {
    "type": "webhook",
    "url": "http://n8n:5678/webhook/omi-create-task",
    "method": "POST"
  }
}
EOF

log_success "Omi Command Center initialized"
log_info "  → REST API:   http://localhost:3200"
log_info "  → WebSocket:  ws://localhost:3201"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 23: KNOWLEDGE BASE — WIKI & DOCUMENTATION SYSTEM (WikiJS)
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                KNOWLEDGE BASE ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  AUTHORS                         WIKI.JS CORE                       STORAGE & SEARCH        │
│  ───────                         ────────────                       ──────────────          │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  ✍️ Web Editor    │          │                               │  │  🗄️ PostgreSQL    │      │
│  │  • WYSIWYG        │─────────▶│     WIKI.JS ENGINE            │─▶│  • Pages          │      │
│  │  • Markdown       │          │                               │  │  • Revisions      │      │
│  │  • Code blocks    │          │  ┌─────────────────────────┐ │  │  • Metadata       │      │
│  │  • Diagrams       │          │  │ RENDERING ENGINE         │ │  └──────────────────┘      │
│  └──────────────────┘          │  │ • Markdown-it            │ │                            │
│                                │  │ • Mermaid diagrams       │ │  ┌──────────────────┐      │
│  ┌──────────────────┐          │  │ • KaTeX math             │ │  │  🔍 Search Engine  │      │
│  │  📝 API Writers   │          │  │ • PlantUML               │ │  │  • Full-text      │      │
│  │  • REST API       │─────────▶│  │ • Code highlighting     │ │─▶│  • Fuzzy match    │      │
│  │  • GraphQL        │          │  └─────────────────────────┘ │  │  • Tag filtering  │      │
│  │  • AI-generated   │          │                               │  └──────────────────┘      │
│  └──────────────────┘          │  ┌─────────────────────────┐ │                            │
│                                │  │ AUTH & ACCESS            │ │  ┌──────────────────┐      │
│  ┌──────────────────┐          │  │ • Local accounts         │ │  │  🔄 Git Sync      │      │
│  │  🔄 Git Sync      │          │  │ • LDAP integration       │ │  │  • Gitea repo     │      │
│  │  • Gitea repos    │◀────────▶│  │ • Group permissions      │ │─▶│  • Auto-commit   │      │
│  │  • Auto-commit    │          │  │ • Page-level ACL         │ │  │  • Version ctrl   │      │
│  │  • Branch sync    │          │  └─────────────────────────┘ │  └──────────────────┘      │
│  └──────────────────┘          └───────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.knowledge-base.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # WIKI.JS — Knowledge Base & Documentation System
  # ═══════════════════════════════════════════════════════════════════════════
  wikijs:
    image: ghcr.io/requarks/wiki:2
    container_name: omni-quantum-wikijs
    ports:
      - "3300:3000"
    environment:
      DB_TYPE: "postgres"
      DB_HOST: "postgres"
      DB_PORT: 5432
      DB_USER: "wikijs"
      DB_PASS: "${WIKIJS_DB_PASSWORD}"
      DB_NAME: "wikijs"

      # ── Server ──
      WIKI_HOST: "http://localhost:3300"
      WIKI_PORT: 3000

      # ── HA Mode ──
      HA_ACTIVE: "false"

      # ── Logging ──
      LOG_LEVEL: "info"
    volumes:
      - wikijs_data:/wiki/data
      - ./config/wikijs/config.yml:/wiki/config.yml:ro
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    labels:
      - "omni.quantum.component=wikijs"
      - "omni.quantum.tier=knowledge"
      - "omni.quantum.system=23"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  wikijs_data:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-knowledge-base.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 23: KNOWLEDGE BASE — WIKI & DOCUMENTATION"

ensure_dir "${DATA_ROOT}/wikijs"
ensure_dir "${CONFIG_ROOT}/wikijs"

ensure_secret "WIKIJS_DB_PASSWORD" 32

create_postgres_db "wikijs" "wikijs" "${WIKIJS_DB_PASSWORD}"

log_success "Knowledge Base (Wiki.js) initialized"
log_info "  → Web UI:  http://localhost:3300"
log_info "  → API:     http://wikijs:3000/graphql"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 24: ANALYTICS ENGINE — BUSINESS INTELLIGENCE (Apache Superset)
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               ANALYTICS ENGINE ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  DATA SOURCES                    SUPERSET CORE                      OUTPUTS                 │
│  ────────────                    ─────────────                      ───────                 │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🗄️ PostgreSQL    │          │                               │  │  📊 Dashboards    │      │
│  │  • All system DBs │─────────▶│     APACHE SUPERSET           │─▶│  • Real-time      │      │
│  │  • Metrics tables │          │                               │  │  • Interactive    │      │
│  └──────────────────┘          │  ┌─────────────────────────┐ │  │  • Embeddable     │      │
│                                │  │ SQL LAB                  │ │  └──────────────────┘      │
│  ┌──────────────────┐          │  │ • Interactive SQL editor │ │                            │
│  │  📁 CSV/Excel     │          │  │ • Query history          │ │  ┌──────────────────┐      │
│  │  • File uploads   │─────────▶│  │ • Auto-complete          │ │  │  📈 Charts         │      │
│  │  • S3/MinIO files │          │  └─────────────────────────┘ │─▶│  • 40+ chart types│      │
│  └──────────────────┘          │                               │  │  • Custom viz     │      │
│                                │  ┌─────────────────────────┐ │  └──────────────────┘      │
│  ┌──────────────────┐          │  │ CHART BUILDER            │ │                            │
│  │  🔗 API Data      │          │  │ • Drag & drop            │ │  ┌──────────────────┐      │
│  │  • REST endpoints │─────────▶│  │ • Calculated columns     │ │  │  📧 Alerts         │      │
│  │  • Nango syncs    │          │  │ • Advanced filters       │ │─▶│  • Scheduled      │      │
│  └──────────────────┘          │  │ • Time series analysis   │ │  │  • Threshold-based│      │
│                                │  └─────────────────────────┘ │  │  • Mattermost     │      │
│  ┌──────────────────┐          │                               │  └──────────────────┘      │
│  │  📊 Prometheus    │          │  ┌─────────────────────────┐ │                            │
│  │  • System metrics │─────────▶│  │ CACHING (Redis)          │ │  ┌──────────────────┐      │
│  │  • App metrics    │          │  │ • Query results           │ │  │  📤 Exports       │      │
│  └──────────────────┘          │  │ • Dashboard renders       │ │─▶│  • PDF/PNG        │      │
│                                │  │ • Metadata                │ │  │  • CSV/Excel      │      │
│                                │  └─────────────────────────┘ │  └──────────────────┘      │
│                                └───────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.analytics.yml
version: "3.9"

x-superset-common: &superset-common
  image: apache/superset:latest
  environment: &superset-env
    # ── Database ──
    DATABASE_DB: "superset"
    DATABASE_HOST: "postgres"
    DATABASE_PORT: 5432
    DATABASE_USER: "superset"
    DATABASE_PASSWORD: "${SUPERSET_DB_PASSWORD}"
    SQLALCHEMY_DATABASE_URI: "postgresql://superset:${SUPERSET_DB_PASSWORD}@postgres:5432/superset"

    # ── Redis ──
    REDIS_HOST: "redis"
    REDIS_PORT: 6379
    REDIS_PASSWORD: "${REDIS_PASSWORD}"
    REDIS_DB: 8

    # ── Security ──
    SUPERSET_SECRET_KEY: "${SUPERSET_SECRET_KEY}"
    ADMIN_USERNAME: "admin"
    ADMIN_PASSWORD: "${SUPERSET_ADMIN_PASSWORD}"
    ADMIN_EMAIL: "admin@omni-quantum.local"

    # ── Features ──
    SUPERSET_LOAD_EXAMPLES: "no"
    MAPBOX_API_KEY: ""
  volumes:
    - superset_home:/app/superset_home
    - ./config/superset/superset_config.py:/app/pythonpath/superset_config.py:ro
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - omni-quantum-network
  logging:
    driver: "json-file"
    options:
      max-size: "50m"
      max-file: "5"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # SUPERSET — Web Application
  # ═══════════════════════════════════════════════════════════════════════════
  superset:
    <<: *superset-common
    container_name: omni-quantum-superset
    command: ["/bin/sh", "-c", "/app/docker/docker-bootstrap.sh app-gunicorn"]
    ports:
      - "8088:8088"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.5"
    labels:
      - "omni.quantum.component=superset"
      - "omni.quantum.tier=analytics"
      - "omni.quantum.system=24"

  # ═══════════════════════════════════════════════════════════════════════════
  # SUPERSET — Celery Worker
  # ═══════════════════════════════════════════════════════════════════════════
  superset-worker:
    <<: *superset-common
    container_name: omni-quantum-superset-worker
    command: ["/bin/sh", "-c", "/app/docker/docker-bootstrap.sh worker"]
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    labels:
      - "omni.quantum.component=superset-worker"

  # ═══════════════════════════════════════════════════════════════════════════
  # SUPERSET — Celery Beat Scheduler
  # ═══════════════════════════════════════════════════════════════════════════
  superset-beat:
    <<: *superset-common
    container_name: omni-quantum-superset-beat
    command: ["/bin/sh", "-c", "/app/docker/docker-bootstrap.sh beat"]
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.25"
    labels:
      - "omni.quantum.component=superset-beat"

  # ═══════════════════════════════════════════════════════════════════════════
  # SUPERSET — Initialization
  # ═══════════════════════════════════════════════════════════════════════════
  superset-init:
    <<: *superset-common
    container_name: omni-quantum-superset-init
    command: ["/bin/sh", "-c", "/app/docker/docker-init.sh"]
    restart: "no"

volumes:
  superset_home:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## CONFIGURATION

```python
# config/superset/superset_config.py
# ═══════════════════════════════════════════════════════════════════════════════
# APACHE SUPERSET — OMNI QUANTUM ELITE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

import os
from datetime import timedelta

# ── Core ──
ROW_LIMIT = 50000
SUPERSET_WEBSERVER_PORT = 8088
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "CHANGE_ME")
SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")

# ── Redis Cache ──
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_DB = int(os.environ.get("REDIS_DB", 8))
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": REDIS_URL,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
FILTER_STATE_CACHE_CONFIG = {**CACHE_CONFIG, "CACHE_DEFAULT_TIMEOUT": 600}

# ── Celery ──
class CeleryConfig:
    broker_url = REDIS_URL
    result_backend = REDIS_URL
    imports = ("superset.sql_lab", "superset.tasks.scheduler")
    task_annotations = {"sql_lab.get_sql_results": {"rate_limit": "100/s"}}
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": timedelta(minutes=1),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": timedelta(minutes=10),
        },
    }

CELERY_CONFIG = CeleryConfig

# ── Features ──
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "EMBEDDED_SUPERSET": True,
    "ALERT_REPORTS": True,
    "DASHBOARD_RBAC": True,
    "ENABLE_EXPLORE_DRAG_AND_DROP": True,
    "GLOBAL_ASYNC_QUERIES": True,
}

# ── Alert Reports (Mattermost) ──
ALERT_REPORTS_NOTIFICATION_DRY_RUN = False
WEBDRIVER_BASEURL = "http://superset:8088/"
WEBDRIVER_TYPE = "chrome"

# ── SQL Lab ──
SQLLAB_ASYNC_TIME_LIMIT_SEC = 600
SQLLAB_TIMEOUT = 300
SQL_MAX_ROW = 100000

# ── Thumbnails ──
THUMBNAIL_SELENIUM_USER = "admin"
THUMBNAIL_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "thumbnail_",
    "CACHE_REDIS_URL": REDIS_URL,
}

# ── Security ──
WTF_CSRF_ENABLED = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set True behind HTTPS proxy
TALISMAN_ENABLED = False
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-analytics.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 24: ANALYTICS ENGINE — APACHE SUPERSET"

ensure_dir "${DATA_ROOT}/superset"
ensure_dir "${CONFIG_ROOT}/superset"

ensure_secret "SUPERSET_DB_PASSWORD" 32
ensure_secret "SUPERSET_SECRET_KEY" 64
ensure_secret "SUPERSET_ADMIN_PASSWORD" 24

create_postgres_db "superset" "superset" "${SUPERSET_DB_PASSWORD}"

log_success "Analytics Engine (Superset) initialized"
log_info "  → Dashboard: http://localhost:8088"
log_info "  → Username:  admin"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 25: SCHEDULING SYSTEM — CALENDAR & BOOKING (Cal.com)
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               SCHEDULING SYSTEM ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  USERS                           CAL.COM CORE                       INTEGRATIONS            │
│  ─────                           ────────────                       ────────────            │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🌐 Booking Page  │          │                               │  │  📧 Email Notify  │      │
│  │  • Public links   │─────────▶│     CAL.COM ENGINE            │─▶│  • Confirmations │      │
│  │  • Embedded forms │          │                               │  │  • Reminders     │      │
│  │  • Team pages     │          │  ┌─────────────────────────┐ │  │  • Cancellations │      │
│  └──────────────────┘          │  │ BOOKING ENGINE            │ │  └──────────────────┘      │
│                                │  │ • Availability calc       │ │                            │
│  ┌──────────────────┐          │  │ • Conflict detection     │ │  ┌──────────────────┐      │
│  │  📱 API Clients   │          │  │ • Buffer time mgmt      │ │  │  💬 Mattermost     │      │
│  │  • REST API       │─────────▶│  │ • Round-robin assign    │ │─▶│  • New bookings  │      │
│  │  • Webhooks       │          │  │ • Recurring events      │ │  │  • Reschedules   │      │
│  │  • n8n triggers   │          │  └─────────────────────────┘ │  │  • Cancellations │      │
│  └──────────────────┘          │                               │  └──────────────────┘      │
│                                │  ┌─────────────────────────┐ │                            │
│  ┌──────────────────┐          │  │ EVENT TYPES              │ │  ┌──────────────────┐      │
│  │  🔄 Calendar Sync │          │  │ • 1-on-1 meetings        │ │  │  🔗 Nango APIs    │      │
│  │  • CalDAV         │◀────────▶│  │ • Group sessions         │ │─▶│  • Google Cal    │      │
│  │  • ICS feeds      │          │  │ • Round-robin            │ │  │  • Outlook       │      │
│  │  • Google/O365    │          │  │ • Collective booking     │ │  │  • Zoom/Meet     │      │
│  └──────────────────┘          │  └─────────────────────────┘ │  └──────────────────┘      │
│                                └───────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.scheduling.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # CAL.COM — Scheduling & Booking Platform
  # ═══════════════════════════════════════════════════════════════════════════
  calcom:
    image: calcom/cal.com:latest
    container_name: omni-quantum-calcom
    ports:
      - "3400:3000"
    environment:
      # ── Database ──
      DATABASE_URL: "postgresql://calcom:${CALCOM_DB_PASSWORD}@postgres:5432/calcom"
      DATABASE_DIRECT_URL: "postgresql://calcom:${CALCOM_DB_PASSWORD}@postgres:5432/calcom"

      # ── Server ──
      NEXT_PUBLIC_WEBAPP_URL: "http://localhost:3400"
      NEXTAUTH_URL: "http://localhost:3400"
      NEXTAUTH_SECRET: "${CALCOM_NEXTAUTH_SECRET}"
      CALENDSO_ENCRYPTION_KEY: "${CALCOM_ENCRYPTION_KEY}"

      # ── Email (via system SMTP) ──
      EMAIL_FROM: "calendar@omni-quantum.local"
      EMAIL_SERVER_HOST: "postal"
      EMAIL_SERVER_PORT: 25
      EMAIL_SERVER_USER: ""
      EMAIL_SERVER_PASSWORD: ""

      # ── Redis ──
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/9"

      # ── Webhooks ──
      CALCOM_WEBHOOK_SECRET: "${CALCOM_WEBHOOK_SECRET}"

      # ── Features ──
      CALCOM_TELEMETRY_DISABLED: 1
      NEXT_PUBLIC_DISABLE_SIGNUP: "false"
      NEXT_PUBLIC_LICENSE_CONSENT: ""
    volumes:
      - calcom_data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 90s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    labels:
      - "omni.quantum.component=calcom"
      - "omni.quantum.tier=scheduling"
      - "omni.quantum.system=25"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  calcom_data:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-scheduling.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 25: SCHEDULING SYSTEM — CAL.COM"

ensure_dir "${DATA_ROOT}/calcom"

ensure_secret "CALCOM_DB_PASSWORD" 32
ensure_secret "CALCOM_NEXTAUTH_SECRET" 64
ensure_secret "CALCOM_ENCRYPTION_KEY" 32
ensure_secret "CALCOM_WEBHOOK_SECRET" 48

create_postgres_db "calcom" "calcom" "${CALCOM_DB_PASSWORD}"

log_success "Scheduling System (Cal.com) initialized"
log_info "  → Web UI:   http://localhost:3400"
log_info "  → API:      http://calcom:3000/api/v1"
```
