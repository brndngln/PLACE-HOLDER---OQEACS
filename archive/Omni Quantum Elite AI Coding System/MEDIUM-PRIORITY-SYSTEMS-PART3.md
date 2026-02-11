# ══════════════════════════════════════════════════════════════════════════════════════════════
# MEDIUM PRIORITY SYSTEMS — PART 3
# OMNI QUANTUM ELITE — ULTIMATE EDITION
# Systems 26-27: CRM, Invoice + System 28: Flowise AI
# ══════════════════════════════════════════════════════════════════════════════════════════════

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 26: CRM SYSTEM — CUSTOMER RELATIONS (Twenty CRM)
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  CRM SYSTEM ARCHITECTURE                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  USERS                           TWENTY CRM CORE                    INTEGRATIONS            │
│  ─────                           ───────────────                    ────────────            │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🌐 Web App       │          │                               │  │  📧 Email         │      │
│  │  • Contact mgmt   │─────────▶│     TWENTY CRM ENGINE         │─▶│  • Email sync    │      │
│  │  • Pipeline view  │          │                               │  │  • Templates     │      │
│  │  • Activity feed  │          │  ┌─────────────────────────┐ │  │  • Tracking      │      │
│  └──────────────────┘          │  │ OBJECTS                  │ │  └──────────────────┘      │
│                                │  │ • People (contacts)      │ │                            │
│  ┌──────────────────┐          │  │ • Companies              │ │  ┌──────────────────┐      │
│  │  📱 API Access    │          │  │ • Opportunities (deals)  │ │  │  📊 Analytics      │      │
│  │  • REST API       │─────────▶│  │ • Tasks & Notes          │ │─▶│  • Pipeline       │      │
│  │  • GraphQL        │          │  │ • Custom objects          │ │  │  • Revenue        │      │
│  │  • Webhooks       │          │  └─────────────────────────┘ │  │  • Activities     │      │
│  └──────────────────┘          │                               │  └──────────────────┘      │
│                                │  ┌─────────────────────────┐ │                            │
│  ┌──────────────────┐          │  │ WORKFLOW ENGINE           │ │  ┌──────────────────┐      │
│  │  🔄 Nango Sync    │          │  │ • Trigger-based          │ │  │  💬 Mattermost     │      │
│  │  • HubSpot import │◀────────▶│  │ • Automations            │ │─▶│  • Deal alerts   │      │
│  │  • Gmail sync     │          │  │ • Scheduled tasks        │ │  │  • Task reminders│      │
│  │  • Calendar sync  │          │  └─────────────────────────┘ │  │  • Activity feed │      │
│  └──────────────────┘          └───────────────────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.crm.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # TWENTY CRM — Server
  # ═══════════════════════════════════════════════════════════════════════════
  twenty-server:
    image: twentycrm/twenty:latest
    container_name: omni-quantum-twenty-server
    ports:
      - "3500:3000"
    environment:
      # ── Server ──
      SERVER_URL: "http://localhost:3500"
      FRONT_BASE_URL: "http://localhost:3500"
      PORT: 3000
      NODE_ENV: "production"

      # ── Database ──
      PG_DATABASE_URL: "postgresql://twenty:${TWENTY_DB_PASSWORD}@postgres:5432/twenty"

      # ── Redis ──
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/10"

      # ── Auth ──
      ACCESS_TOKEN_SECRET: "${TWENTY_ACCESS_TOKEN_SECRET}"
      LOGIN_TOKEN_SECRET: "${TWENTY_LOGIN_TOKEN_SECRET}"
      REFRESH_TOKEN_SECRET: "${TWENTY_REFRESH_TOKEN_SECRET}"
      FILE_TOKEN_SECRET: "${TWENTY_FILE_TOKEN_SECRET}"

      # ── Storage (MinIO) ──
      STORAGE_TYPE: "s3"
      STORAGE_S3_REGION: "us-east-1"
      STORAGE_S3_NAME: "uploads"
      STORAGE_S3_ENDPOINT: "http://minio:9000"
      STORAGE_S3_ACCESS_KEY_ID: "${MINIO_ROOT_USER}"
      STORAGE_S3_SECRET_ACCESS_KEY: "${MINIO_ROOT_PASSWORD}"

      # ── Email ──
      EMAIL_FROM_ADDRESS: "crm@omni-quantum.local"
      EMAIL_SYSTEM_ADDRESS: "system@omni-quantum.local"
      EMAIL_FROM_NAME: "Omni Quantum CRM"

      # ── Features ──
      TELEMETRY_ENABLED: "false"
      SIGN_IN_PREFILLED: "false"
      IS_BILLING_ENABLED: "false"
      CALENDAR_PROVIDER_GOOGLE_ENABLED: "false"

      # ── Messaging (n8n webhook for Mattermost) ──
      WEBHOOK_URL: "http://n8n:5678/webhook/crm-events"
    volumes:
      - twenty_data:/app/.local-storage
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/healthz"]
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
      - "omni.quantum.component=twenty-crm"
      - "omni.quantum.tier=crm"
      - "omni.quantum.system=26"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # ═══════════════════════════════════════════════════════════════════════════
  # TWENTY CRM — Worker (Background Jobs)
  # ═══════════════════════════════════════════════════════════════════════════
  twenty-worker:
    image: twentycrm/twenty:latest
    container_name: omni-quantum-twenty-worker
    command: ["yarn", "worker:prod"]
    environment:
      PG_DATABASE_URL: "postgresql://twenty:${TWENTY_DB_PASSWORD}@postgres:5432/twenty"
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/10"
      ACCESS_TOKEN_SECRET: "${TWENTY_ACCESS_TOKEN_SECRET}"
      STORAGE_TYPE: "s3"
      STORAGE_S3_ENDPOINT: "http://minio:9000"
      STORAGE_S3_ACCESS_KEY_ID: "${MINIO_ROOT_USER}"
      STORAGE_S3_SECRET_ACCESS_KEY: "${MINIO_ROOT_PASSWORD}"
      STORAGE_S3_NAME: "uploads"
      STORAGE_S3_REGION: "us-east-1"
    depends_on:
      - twenty-server
    networks:
      - omni-quantum-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "0.5"
    labels:
      - "omni.quantum.component=twenty-worker"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  twenty_data:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-crm.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 26: CRM SYSTEM — TWENTY CRM"

ensure_dir "${DATA_ROOT}/twenty"

ensure_secret "TWENTY_DB_PASSWORD" 32
ensure_secret "TWENTY_ACCESS_TOKEN_SECRET" 64
ensure_secret "TWENTY_LOGIN_TOKEN_SECRET" 64
ensure_secret "TWENTY_REFRESH_TOKEN_SECRET" 64
ensure_secret "TWENTY_FILE_TOKEN_SECRET" 64

create_postgres_db "twenty" "twenty" "${TWENTY_DB_PASSWORD}"

log_success "CRM System (Twenty) initialized"
log_info "  → Web UI:   http://localhost:3500"
log_info "  → GraphQL:  http://localhost:3500/api"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 27: INVOICE SYSTEM — BILLING & PAYMENTS (Crater)
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                INVOICE SYSTEM ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  USERS                           CRATER CORE                        OUTPUTS                 │
│  ─────                           ───────────                        ───────                 │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🌐 Web Dashboard │          │                               │  │  📄 PDF Invoices  │      │
│  │  • Create invoices│─────────▶│     CRATER INVOICE ENGINE     │─▶│  • Auto-generate │      │
│  │  • Track payments │          │                               │  │  • Custom themes │      │
│  │  • Manage clients │          │  ┌─────────────────────────┐ │  │  • Email delivery│      │
│  └──────────────────┘          │  │ INVOICING                │ │  └──────────────────┘      │
│                                │  │ • Create/Edit/Send       │ │                            │
│  ┌──────────────────┐          │  │ • Recurring invoices     │ │  ┌──────────────────┐      │
│  │  📱 API Access    │          │  │ • Auto-reminders         │ │  │  📊 Reports       │      │
│  │  • REST API       │─────────▶│  │ • Tax calculations      │ │─▶│  • Revenue       │      │
│  │  • n8n webhooks   │          │  └─────────────────────────┘ │  │  • Expenses      │      │
│  │  • CRM triggers   │          │                               │  │  • Tax summary   │      │
│  └──────────────────┘          │  ┌─────────────────────────┐ │  │  • P&L           │      │
│                                │  │ ESTIMATES                │ │  └──────────────────┘      │
│                                │  │ • Quote generation       │ │                            │
│                                │  │ • Convert to invoice     │ │  ┌──────────────────┐      │
│                                │  │ • Client approval        │ │  │  💬 Notifications │      │
│                                │  └─────────────────────────┘ │─▶│  • Payment recv  │      │
│                                │                               │  │  • Overdue alerts│      │
│                                │  ┌─────────────────────────┐ │  │  • Mattermost    │      │
│                                │  │ EXPENSE TRACKING         │ │  └──────────────────┘      │
│                                │  │ • Categories             │ │                            │
│                                │  │ • Receipt uploads        │ │  ┌──────────────────┐      │
│                                │  │ • Vendor management      │ │  │  🔗 CRM Link      │      │
│                                │  └─────────────────────────┘ │─▶│  • Twenty CRM    │      │
│                                └───────────────────────────────┘  │  • Auto-sync     │      │
│                                                                    └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.invoice.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # CRATER — Invoice & Billing System
  # ═══════════════════════════════════════════════════════════════════════════
  crater:
    image: craterapp/crater:latest
    container_name: omni-quantum-crater
    ports:
      - "3600:80"
    environment:
      APP_NAME: "Omni Quantum Billing"
      APP_ENV: "production"
      APP_DEBUG: "false"
      APP_URL: "http://localhost:3600"
      APP_KEY: "${CRATER_APP_KEY}"

      # ── Database ──
      DB_CONNECTION: "pgsql"
      DB_HOST: "postgres"
      DB_PORT: 5432
      DB_DATABASE: "crater"
      DB_USERNAME: "crater"
      DB_PASSWORD: "${CRATER_DB_PASSWORD}"

      # ── Redis ──
      REDIS_HOST: "redis"
      REDIS_PASSWORD: "${REDIS_PASSWORD}"
      REDIS_PORT: 6379
      REDIS_DB: 11
      CACHE_DRIVER: "redis"
      SESSION_DRIVER: "redis"
      QUEUE_CONNECTION: "redis"

      # ── Mail ──
      MAIL_MAILER: "smtp"
      MAIL_HOST: "postal"
      MAIL_PORT: 25
      MAIL_FROM_ADDRESS: "billing@omni-quantum.local"
      MAIL_FROM_NAME: "Omni Quantum Billing"

      # ── Storage (MinIO) ──
      FILESYSTEM_DISK: "s3"
      AWS_ACCESS_KEY_ID: "${MINIO_ROOT_USER}"
      AWS_SECRET_ACCESS_KEY: "${MINIO_ROOT_PASSWORD}"
      AWS_DEFAULT_REGION: "us-east-1"
      AWS_BUCKET: "documents"
      AWS_ENDPOINT: "http://minio:9000"
      AWS_USE_PATH_STYLE_ENDPOINT: "true"

      # ── PDF Generation ──
      PDF_DRIVER: "dompdf"

      # ── Logging ──
      LOG_CHANNEL: "stderr"
    volumes:
      - crater_data:/crater/storage
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
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
      - "omni.quantum.component=crater"
      - "omni.quantum.tier=billing"
      - "omni.quantum.system=27"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  crater_data:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-invoice.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 27: INVOICE SYSTEM — CRATER BILLING"

ensure_dir "${DATA_ROOT}/crater"

ensure_secret "CRATER_DB_PASSWORD" 32
CRATER_APP_KEY="base64:$(openssl rand -base64 32)"
set_env "CRATER_APP_KEY" "${CRATER_APP_KEY}"

create_postgres_db "crater" "crater" "${CRATER_DB_PASSWORD}"

log_success "Invoice System (Crater) initialized"
log_info "  → Web UI: http://localhost:3600"
log_info "  → API:    http://crater:80/api/v1"
```

---

# ══════════════════════════════════════════════════════════════════════════════════════════════
# SYSTEM 28: FLOWISE AI — LOW-CODE AI WORKFLOW BUILDER
# ══════════════════════════════════════════════════════════════════════════════════════════════

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                              ║
║    ███████╗██╗      ██████╗ ██╗    ██╗██╗███████╗███████╗     █████╗ ██╗                     ║
║    ██╔════╝██║     ██╔═══██╗██║    ██║██║██╔════╝██╔════╝    ██╔══██╗██║                     ║
║    █████╗  ██║     ██║   ██║██║ █╗ ██║██║███████╗█████╗      ███████║██║                     ║
║    ██╔══╝  ██║     ██║   ██║██║███╗██║██║╚════██║██╔══╝      ██╔══██║██║                     ║
║    ██║     ███████╗╚██████╔╝╚███╔███╔╝██║███████║███████╗    ██║  ██║██║                     ║
║    ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ ╚═╝╚══════╝╚══════╝    ╚═╝  ╚═╝╚═╝                     ║
║                                                                                              ║
║                 "Build AI Agents & Chatbots Visually. Deploy Instantly."                      ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  FLOWISE AI ARCHITECTURE                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  BUILDERS                        FLOWISE CORE                       EXECUTION               │
│  ────────                        ────────────                       ─────────               │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🎨 Visual Canvas │          │                               │  │  🤖 Chatflows     │      │
│  │  • Drag & drop    │─────────▶│     FLOWISE ENGINE            │─▶│  • Conversational │      │
│  │  • Node-based     │          │                               │  │  • Multi-turn     │      │
│  │  • Real-time test │          │  ┌─────────────────────────┐ │  │  • Streaming      │      │
│  └──────────────────┘          │  │ LLM NODES               │ │  └──────────────────┘      │
│                                │  │ • ChatOpenAI (→LiteLLM)  │ │                            │
│  ┌──────────────────┐          │  │ • Ollama (local)         │ │  ┌──────────────────┐      │
│  │  📡 API Deploy    │          │  │ • HuggingFace            │ │  │  🔗 Agentflows    │      │
│  │  • REST endpoint  │─────────▶│  │ • Groq                   │ │─▶│  • Tool-using    │      │
│  │  • Embed widget   │          │  │ • Custom LLM             │ │  │  • Multi-agent   │      │
│  │  • WebSocket      │          │  └─────────────────────────┘ │  │  • Sequential    │      │
│  └──────────────────┘          │                               │  └──────────────────┘      │
│                                │  ┌─────────────────────────┐ │                            │
│  ┌──────────────────┐          │  │ MEMORY & RETRIEVAL       │ │  ┌──────────────────┐      │
│  │  🔄 n8n Trigger   │          │  │ • Qdrant vector store    │ │  │  📊 Analytics      │      │
│  │  • Webhook calls  │─────────▶│  │ • PostgreSQL pgvector   │ │─▶│  • Langfuse trace │      │
│  │  • Chatflow API   │          │  │ • In-memory              │ │  │  • Usage metrics  │      │
│  │  • Schedule-based │          │  │ • Redis chat history     │ │  │  • Cost tracking  │      │
│  └──────────────────┘          │  └─────────────────────────┘ │  └──────────────────┘      │
│                                │                               │                            │
│  ┌──────────────────┐          │  ┌─────────────────────────┐ │  ┌──────────────────┐      │
│  │  🧩 Custom Nodes  │          │  │ TOOL NODES               │ │  │  💬 Mattermost     │      │
│  │  • Python tools   │─────────▶│  │ • Web scraper            │ │─▶│  • AI chatbot    │      │
│  │  • API connectors │          │  │ • Calculator              │ │  │  • Agent replies │      │
│  │  • DB queries     │          │  │ • Code interpreter       │ │  │  • Notifications │      │
│  └──────────────────┘          │  │ • API chain               │ │  └──────────────────┘      │
│                                │  │ • Custom function         │ │                            │
│                                │  │ • Mattermost tool         │ │                            │
│                                │  └─────────────────────────┘ │                            │
│                                └───────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.flowise.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # FLOWISE AI — Visual AI Workflow Builder
  # ═══════════════════════════════════════════════════════════════════════════
  flowise:
    image: flowiseai/flowise:latest
    container_name: omni-quantum-flowise
    ports:
      - "3700:3000"
    environment:
      # ── Server ──
      PORT: 3000
      FLOWISE_HOST: "0.0.0.0"
      APIKEY_PATH: "/root/.flowise"
      LOG_LEVEL: "info"
      DEBUG: "false"

      # ── Database ──
      DATABASE_TYPE: "postgres"
      DATABASE_HOST: "postgres"
      DATABASE_PORT: 5432
      DATABASE_NAME: "flowise"
      DATABASE_USER: "flowise"
      DATABASE_PASSWORD: "${FLOWISE_DB_PASSWORD}"

      # ── Auth ──
      FLOWISE_USERNAME: "admin"
      FLOWISE_PASSWORD: "${FLOWISE_ADMIN_PASSWORD}"
      FLOWISE_SECRETKEY_OVERWRITE: "${FLOWISE_SECRET_KEY}"

      # ── Storage ──
      BLOB_STORAGE_PATH: "/root/.flowise/storage"
      STORAGE_TYPE: "s3"
      S3_STORAGE_BUCKET_NAME: "artifacts"
      S3_STORAGE_ACCESS_KEY_ID: "${MINIO_ROOT_USER}"
      S3_STORAGE_SECRET_ACCESS_KEY: "${MINIO_ROOT_PASSWORD}"
      S3_STORAGE_REGION: "us-east-1"
      S3_ENDPOINT_URL: "http://minio:9000"
      S3_FORCE_PATH_STYLE: "true"

      # ── LLM Defaults (all routed through LiteLLM / Token Infinity) ──
      DEFAULT_OPENAI_API_KEY: "${LITELLM_API_KEY}"
      DEFAULT_OPENAI_BASE_URL: "http://litellm:4000/v1"

      # ── Vector Store (Qdrant) ──
      QDRANT_URL: "http://qdrant:6333"
      QDRANT_API_KEY: "${QDRANT_API_KEY}"

      # ── Observability ──
      LANGFUSE_PUBLIC_KEY: "${LANGFUSE_PUBLIC_KEY}"
      LANGFUSE_SECRET_KEY: "${LANGFUSE_SECRET_KEY}"
      LANGFUSE_HOST: "http://langfuse:3000"

      # ── Rate Limiting ──
      RATE_LIMITER_ENABLED: "true"
      RATE_LIMITER_POINTS: 100
      RATE_LIMITER_DURATION: 60

      # ── Features ──
      TOOL_FUNCTION_BUILTIN_DEP: "axios,cheerio,moment,lodash"
      TOOL_FUNCTION_EXTERNAL_DEP: ""
      NUMBER_OF_PROXIES: 0

      # ── Telemetry ──
      DISABLE_FLOWISE_TELEMETRY: "true"
    volumes:
      - flowise_data:/root/.flowise
      - ./config/flowise/chatflows:/root/.flowise/chatflows:ro
    depends_on:
      postgres:
        condition: service_healthy
      litellm:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/v1/ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 45s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.5"
        reservations:
          memory: 512M
    labels:
      - "omni.quantum.component=flowise"
      - "omni.quantum.tier=ai-builder"
      - "omni.quantum.system=28"
      - "prometheus.scrape=true"
      - "prometheus.port=3000"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  flowise_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${DATA_ROOT:-/opt/omni-quantum/data}/flowise

networks:
  omni-quantum-network:
    external: true
```

## PYTHON SDK — FLOWISE CLIENT

```python
# sdk/flowise_client.py
# ═══════════════════════════════════════════════════════════════════════════════
# FLOWISE AI SDK — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enterprise Flowise client for chatflow execution, agent deployment,
and programmatic AI workflow management.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import aiohttp

logger = logging.getLogger("omni.quantum.flowise")


@dataclass
class ChatflowResponse:
    text: str
    chatflow_id: str
    chat_id: str = ""
    source_documents: list[dict] = field(default_factory=list)
    used_tools: list[str] = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)


class FlowiseClient:
    """Async client for Flowise AI visual workflow platform."""

    def __init__(
        self,
        base_url: str = "http://flowise:3000",
        api_key: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def predict(
        self,
        chatflow_id: str,
        question: str,
        chat_id: Optional[str] = None,
        overrides: Optional[dict] = None,
        uploads: Optional[list[dict]] = None,
    ) -> ChatflowResponse:
        """Send a prediction request to a chatflow."""
        session = await self._get_session()
        payload: dict[str, Any] = {"question": question}
        if chat_id:
            payload["chatId"] = chat_id
        if overrides:
            payload["overrideConfig"] = overrides
        if uploads:
            payload["uploads"] = uploads

        async with session.post(
            f"{self.base_url}/api/v1/prediction/{chatflow_id}",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return ChatflowResponse(
                text=data.get("text", data.get("json", {}).get("text", "")),
                chatflow_id=chatflow_id,
                chat_id=data.get("chatId", ""),
                source_documents=data.get("sourceDocuments", []),
                used_tools=data.get("usedTools", []),
                token_usage=data.get("chatMessageId", {}),
            )

    async def predict_stream(
        self,
        chatflow_id: str,
        question: str,
        chat_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream a prediction response token by token."""
        session = await self._get_session()
        payload: dict[str, Any] = {"question": question, "streaming": True}
        if chat_id:
            payload["chatId"] = chat_id

        async with session.post(
            f"{self.base_url}/api/v1/prediction/{chatflow_id}",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data: "):
                    chunk = decoded[6:]
                    if chunk == "[DONE]":
                        break
                    try:
                        parsed = json.loads(chunk)
                        if "token" in parsed:
                            yield parsed["token"]
                    except json.JSONDecodeError:
                        yield chunk

    async def list_chatflows(self) -> list[dict]:
        """List all available chatflows."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/v1/chatflows") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_chatflow(self, chatflow_id: str) -> dict:
        """Get chatflow details."""
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/api/v1/chatflows/{chatflow_id}"
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def create_chatflow(self, chatflow_data: dict) -> dict:
        """Create a new chatflow programmatically."""
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/v1/chatflows",
            json=chatflow_data,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def upsert_vector(
        self,
        chatflow_id: str,
        document: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Upsert document into a chatflow's vector store."""
        session = await self._get_session()
        payload = {"document": document}
        if metadata:
            payload["metadata"] = metadata
        async with session.post(
            f"{self.base_url}/api/v1/vector/upsert/{chatflow_id}",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_chat_history(
        self,
        chatflow_id: str,
        chat_id: Optional[str] = None,
        sort_order: str = "DESC",
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve chat message history."""
        session = await self._get_session()
        params = {
            "chatflowid": chatflow_id,
            "order": sort_order,
            "limit": limit,
        }
        if chat_id:
            params["chatId"] = chat_id
        async with session.get(
            f"{self.base_url}/api/v1/chatmessage", params=params
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
# scripts/init-flowise.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 28: FLOWISE AI — VISUAL AI WORKFLOW BUILDER"

ensure_dir "${DATA_ROOT}/flowise"
ensure_dir "${CONFIG_ROOT}/flowise/chatflows"

ensure_secret "FLOWISE_DB_PASSWORD" 32
ensure_secret "FLOWISE_ADMIN_PASSWORD" 24
ensure_secret "FLOWISE_SECRET_KEY" 64

create_postgres_db "flowise" "flowise" "${FLOWISE_DB_PASSWORD}"

log_success "Flowise AI initialized successfully"
log_info "  → Web Builder: http://localhost:3700"
log_info "  → API:         http://flowise:3000/api/v1"
log_info "  → Username:    admin"
```

---

# ══════════════════════════════════════════════════════════════════════════════════════════════
# MEDIUM PRIORITY — MASTER SETUP SCRIPT
# ══════════════════════════════════════════════════════════════════════════════════════════════

```bash
#!/usr/bin/env bash
# scripts/setup-medium-priority.sh
# ═══════════════════════════════════════════════════════════════════════════════
# OMNI QUANTUM ELITE — MEDIUM PRIORITY SYSTEMS MASTER SETUP
# Systems 18-28: AI Agents, Storage, Integrations, Business Tools, Flowise AI
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

cat << 'BANNER'
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║   ██████╗ ███╗   ███╗███╗   ██╗██╗     ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗    ║
║  ██╔═══██╗████╗ ████║████╗  ██║██║    ██╔═══██╗██║   ██║██╔══██╗████╗  ██║    ║
║  ██║   ██║██╔████╔██║██╔██╗ ██║██║    ██║   ██║██║   ██║███████║██╔██╗ ██║    ║
║  ██║   ██║██║╚██╔╝██║██║╚██╗██║██║    ██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║    ║
║  ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║    ╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║    ║
║   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝     ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝    ║
║                                                                                  ║
║              MEDIUM PRIORITY SYSTEMS + FLOWISE AI — SETUP                        ║
║              Systems 18–28 | AI Agents • Storage • Integrations                  ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
BANNER

START_TIME=$(date +%s)

log_header "PHASE 1: AI AGENTS (Systems 18-19)"
bash "${SCRIPT_DIR}/init-openhands.sh"
bash "${SCRIPT_DIR}/init-swe-agent.sh"

log_header "PHASE 2: INTEGRATIONS & STORAGE (Systems 20-21)"
bash "${SCRIPT_DIR}/init-nango.sh"
bash "${SCRIPT_DIR}/init-minio.sh"

log_header "PHASE 3: WEARABLE & KNOWLEDGE (Systems 22-23)"
bash "${SCRIPT_DIR}/init-omi.sh"
bash "${SCRIPT_DIR}/init-knowledge-base.sh"

log_header "PHASE 4: ANALYTICS & SCHEDULING (Systems 24-25)"
bash "${SCRIPT_DIR}/init-analytics.sh"
bash "${SCRIPT_DIR}/init-scheduling.sh"

log_header "PHASE 5: BUSINESS TOOLS (Systems 26-27)"
bash "${SCRIPT_DIR}/init-crm.sh"
bash "${SCRIPT_DIR}/init-invoice.sh"

log_header "PHASE 6: AI BUILDER (System 28)"
bash "${SCRIPT_DIR}/init-flowise.sh"

log_header "PHASE 7: DOCKER COMPOSE UP"
COMPOSE_FILES=(
  "docker-compose.openhands.yml"
  "docker-compose.swe-agent.yml"
  "docker-compose.nango.yml"
  "docker-compose.minio.yml"
  "docker-compose.omi.yml"
  "docker-compose.knowledge-base.yml"
  "docker-compose.analytics.yml"
  "docker-compose.scheduling.yml"
  "docker-compose.crm.yml"
  "docker-compose.invoice.yml"
  "docker-compose.flowise.yml"
)

COMPOSE_CMD="docker compose"
for f in "${COMPOSE_FILES[@]}"; do
  COMPOSE_CMD+=" -f ${f}"
done
${COMPOSE_CMD} up -d

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

cat << EOF

╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║  ✅  MEDIUM PRIORITY SYSTEMS + FLOWISE AI — DEPLOYMENT COMPLETE                  ║
║                                                                                  ║
║  Duration: ${DURATION}s                                                          ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  SYSTEM 18  OpenHands AI Agent     http://localhost:3100                          ║
║  SYSTEM 19  SWE-Agent              http://localhost:3101                          ║
║  SYSTEM 20  Nango Integrations     http://localhost:3103                          ║
║  SYSTEM 21  MinIO Storage          http://localhost:9001  (API: 9000)             ║
║  SYSTEM 22  Omi Command Center     http://localhost:3200  (WS: 3201)             ║
║  SYSTEM 23  Wiki.js Knowledge      http://localhost:3300                          ║
║  SYSTEM 24  Superset Analytics     http://localhost:8088                          ║
║  SYSTEM 25  Cal.com Scheduling     http://localhost:3400                          ║
║  SYSTEM 26  Twenty CRM             http://localhost:3500                          ║
║  SYSTEM 27  Crater Invoicing       http://localhost:3600                          ║
║  SYSTEM 28  Flowise AI Builder     http://localhost:3700                          ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  PROGRESS:                                                                       ║
║  CRITICAL (1-7):    ████████████████████ 100% ✅                                  ║
║  HIGH (8-17):       ████████████████████ 100% ✅                                  ║
║  MEDIUM (18-28):    ████████████████████ 100% ✅                                  ║
║  STANDARD (29-37):  ░░░░░░░░░░░░░░░░░░░░   0% 📋 NEXT                           ║
║                                                                                  ║
║  Overall: 28/37 systems (76%)                                                    ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝

EOF
```

---

# ══════════════════════════════════════════════════════════════════════════════════════════════
# COMPLETE INTEGRATION MAP — ALL 28 SYSTEMS
# ══════════════════════════════════════════════════════════════════════════════════════════════

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                      │
│                           OMNI QUANTUM ELITE — COMPLETE SYSTEM INTERCONNECTION                        │
│                                      28 SERVICES • ZERO DEPENDENCIES                                 │
│                                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    🧠 AI LAYER                                                  │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │  │
│  │  │  LiteLLM   │ │  Ollama    │ │  Langfuse  │ │  Qdrant    │ │  OpenHands │ │  SWE-Agent │    │  │
│  │  │ (Gateway)  │ │ (Local LLM)│ │ (Observe)  │ │ (Vectors)  │ │ (AI Coder) │ │ (Auto-Fix) │    │  │
│  │  │  :4000     │ │  :11434    │ │  :3000     │ │  :6333     │ │  :3100     │ │  :3101     │    │  │
│  │  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘    │  │
│  │         │               │              │              │              │              │           │  │
│  │  ┌──────┴───────────────┴──────────────┴──────────────┴──────────────┴──────────────┴────────┐  │  │
│  │  │                            TOKEN INFINITY SYSTEM (System 11)                              │  │  │
│  │  │                        Unlimited LLM access • Zero cost • Auto-failover                  │  │  │
│  │  └──────────────────────────────────────────┬───────────────────────────────────────────────┘  │  │
│  │                                              │                                                 │  │
│  │  ┌────────────┐                              │                                                 │  │
│  │  │  Flowise   │◀─────────────────────────────┘                                                 │  │
│  │  │ (AI Build) │   Visual AI agent/chatbot builder routed through Token Infinity                │  │
│  │  │  :3700     │                                                                                │  │
│  │  └────────────┘                                                                                │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 ⚡ AUTOMATION & INTEGRATION LAYER                               │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                                   │  │
│  │  │  n8n       │ │  Nango     │ │  Gitea     │ │  Plane     │                                   │  │
│  │  │ (Workflow) │ │ (APIs)     │ │ (Git)      │ │ (Projects) │                                   │  │
│  │  │  :5678     │ │  :3103     │ │  :3000     │ │  :80       │                                   │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘                                   │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    💼 BUSINESS LAYER                                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │  │
│  │  │  Twenty    │ │  Crater    │ │  Cal.com   │ │  Wiki.js   │ │  Superset  │ │  Omi       │    │  │
│  │  │ (CRM)     │ │ (Invoice)  │ │ (Schedule) │ │ (Wiki)     │ │ (BI)       │ │ (Wearable) │    │  │
│  │  │  :3500     │ │  :3600     │ │  :3400     │ │  :3300     │ │  :8088     │ │  :3200     │    │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                  🔧 INFRASTRUCTURE LAYER                                        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                    │  │
│  │  │ PostgreSQL │ │  Redis     │ │  MinIO     │ │ Mattermost │ │  Traefik   │                    │  │
│  │  │ (Database) │ │ (Cache)    │ │ (S3)       │ │ (Chat)     │ │ (Proxy)    │                    │  │
│  │  │  :5432     │ │  :6379     │ │  :9000     │ │  :8065     │ │  :80/:443  │                    │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘                    │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# ══════════════════════════════════════════════════════════════════════════════════════════════
# PORT REGISTRY — ALL MEDIUM PRIORITY + FLOWISE SYSTEMS
# ══════════════════════════════════════════════════════════════════════════════════════════════

| System | Service | Port(s) | Protocol |
|--------|---------|---------|----------|
| 18 | OpenHands AI Agent | 3100 | HTTP |
| 19 | SWE-Agent API | 3101 | HTTP |
| 20 | Nango Server | 3103 | HTTP |
| 21 | MinIO S3 API | 9000 | HTTP/S3 |
| 21 | MinIO Console | 9001 | HTTP |
| 22 | Omi Bridge REST | 3200 | HTTP |
| 22 | Omi Bridge WebSocket | 3201 | WS |
| 23 | Wiki.js | 3300 | HTTP |
| 24 | Apache Superset | 8088 | HTTP |
| 25 | Cal.com | 3400 | HTTP |
| 26 | Twenty CRM | 3500 | HTTP |
| 27 | Crater Invoice | 3600 | HTTP |
| 28 | Flowise AI | 3700 | HTTP |

---

# ══════════════════════════════════════════════════════════════════════════════════════════════
# REDIS DB ALLOCATION — COMPLETE REGISTRY
# ══════════════════════════════════════════════════════════════════════════════════════════════

| DB # | Service | Purpose |
|------|---------|---------|
| 0 | Default | General cache |
| 1 | Mattermost | Session/cache |
| 2 | n8n Queue | Job queue |
| 3 | LiteLLM | Response cache |
| 4 | Plane | Task queue |
| 5 | SWE-Agent | Celery broker |
| 6 | Nango | Sync state |
| 7 | Omi Bridge | Session/events |
| 8 | Superset | Cache/Celery |
| 9 | Cal.com | Session/cache |
| 10 | Twenty CRM | Cache/queue |
| 11 | Crater | Cache/session |
| 12 | Flowise | Internal cache |
| 13-15 | Reserved | Future systems |
