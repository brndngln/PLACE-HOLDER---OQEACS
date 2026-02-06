# ══════════════════════════════════════════════════════════════════════════════════════════════
# MEDIUM PRIORITY SYSTEMS (18-27) + FLOWISE AI — PART 1
# OMNI QUANTUM ELITE — ULTIMATE EDITION
# Systems 18-21: OpenHands, SWE-Agent, Nango, MinIO
# ══════════════════════════════════════════════════════════════════════════════════════════════

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                              ║
║    ███╗   ███╗███████╗██████╗ ██╗██╗   ██╗███╗   ███╗    ████████╗██╗███████╗██████╗         ║
║    ████╗ ████║██╔════╝██╔══██╗██║██║   ██║████╗ ████║    ╚══██╔══╝██║██╔════╝██╔══██╗        ║
║    ██╔████╔██║█████╗  ██║  ██║██║██║   ██║██╔████╔██║       ██║   ██║█████╗  ██████╔╝        ║
║    ██║╚██╔╝██║██╔══╝  ██║  ██║██║██║   ██║██║╚██╔╝██║       ██║   ██║██╔══╝  ██╔══██╗        ║
║    ██║ ╚═╝ ██║███████╗██████╔╝██║╚██████╔╝██║ ╚═╝ ██║       ██║   ██║███████╗██║  ██║        ║
║    ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝ ╚═════╝ ╚═╝     ╚═╝       ╚═╝   ╚═╝╚══════╝╚═╝  ╚═╝        ║
║                                                                                              ║
║                      "Autonomous Agents. Infinite Integrations. Zero Limits."                 ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 18: OPENHANDS — AI CODING AGENT
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   OPENHANDS ARCHITECTURE                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  USER REQUEST                    OPENHANDS CORE                     EXECUTION               │
│  ───────────                     ──────────────                     ─────────                │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  💬 Natural Lang  │          │                               │  │  📁 File System   │      │
│  │  • "Build a REST  │─────────▶│     AGENT CONTROLLER          │─▶│  • Read/Write     │      │
│  │    API for..."    │          │                               │  │  • Create/Delete  │      │
│  │  • "Fix bug in.." │          │  • CodeAct Agent (primary)    │  │  • Navigate dirs  │      │
│  │  • "Refactor..."  │          │  • Browsing Agent             │  └──────────────────┘      │
│  └──────────────────┘          │  • Monologue Agent            │                            │
│                                │  • Delegator Agent            │  ┌──────────────────┐      │
│  ┌──────────────────┐          │                               │  │  🖥️ Terminal       │      │
│  │  🔗 API Triggers  │          │  LLM BACKENDS:                │─▶│  • Bash commands  │      │
│  │  • Gitea webhooks │─────────▶│  ┌───────────────────────┐   │  │  • Install deps   │      │
│  │  • Mattermost bot │          │  │ LiteLLM Gateway ──────│───│  │  • Run tests      │      │
│  │  • n8n workflows  │          │  │ • Local: Ollama        │   │  │  • Git operations │      │
│  │  • REST endpoint  │          │  │ • Cloud: Groq/Gemini   │   │  └──────────────────┘      │
│  └──────────────────┘          │  │ • Aggregator: OpenRouter│   │                            │
│                                │  └───────────────────────┘   │  ┌──────────────────┐      │
│  ┌──────────────────┐          │                               │  │  🌐 Browser        │      │
│  │  📋 Plane Issues  │          │  SANDBOXED EXECUTION:         │─▶│  • Web research   │      │
│  │  • Auto-assigned  │─────────▶│  ┌───────────────────────┐   │  │  • Doc lookup     │      │
│  │  • Priority-based │          │  │ Docker-in-Docker       │   │  │  • API docs       │      │
│  │  • Sprint tasks   │          │  │ • Isolated workspace   │   │  └──────────────────┘      │
│  └──────────────────┘          │  │ • Per-task containers   │   │                            │
│                                │  │ • Resource limits       │   │  ┌──────────────────┐      │
│                                │  │ • Auto-cleanup          │   │  │  📊 Langfuse       │      │
│                                │  └───────────────────────┘   │─▶│  • Trace all runs  │      │
│                                │                               │  │  • Cost tracking   │      │
│                                └───────────────────────────────┘  │  • Quality scores  │      │
│                                                                    └──────────────────┘      │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.openhands.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # OPENHANDS — AI CODING AGENT
  # ═══════════════════════════════════════════════════════════════════════════
  openhands:
    image: docker.all-hands.dev/all-hands-ai/openhands:latest
    container_name: omni-quantum-openhands
    ports:
      - "3100:3000"
    environment:
      # ── LLM Configuration (via LiteLLM Gateway) ──
      LLM_MODEL: "litellm/ollama/deepseek-coder-v2"
      LLM_API_KEY: "${LITELLM_API_KEY}"
      LLM_BASE_URL: "http://litellm:4000/v1"
      LLM_EMBEDDING_MODEL: "litellm/ollama/nomic-embed-text"

      # ── Workspace ──
      WORKSPACE_BASE: "/opt/workspace"
      WORKSPACE_MOUNT_PATH: "${OPENHANDS_WORKSPACE:-/opt/omni-quantum/workspaces/openhands}"
      WORKSPACE_MOUNT_REWRITE: "/opt/workspace"

      # ── Sandbox Configuration ──
      SANDBOX_TYPE: "docker"
      SANDBOX_CONTAINER_IMAGE: "docker.all-hands.dev/all-hands-ai/runtime:latest"
      SANDBOX_USER_ID: 1000
      SANDBOX_TIMEOUT: 300
      SANDBOX_ENABLE_AUTO_LINT: true
      SANDBOX_INIT_PLUGINS: "JupyterRequirement,AgentSkillsRequirement"

      # ── Agent Configuration ──
      DEFAULT_AGENT: "CodeActAgent"
      MAX_ITERATIONS: 100
      MAX_BUDGET_PER_TASK: 0   # Unlimited (routed through Token Infinity)

      # ── Observability ──
      LANGFUSE_PUBLIC_KEY: "${LANGFUSE_PUBLIC_KEY}"
      LANGFUSE_SECRET_KEY: "${LANGFUSE_SECRET_KEY}"
      LANGFUSE_HOST: "http://langfuse:3000"

      # ── Security ──
      JWT_SECRET: "${OPENHANDS_JWT_SECRET}"
      GITHUB_TOKEN: ""  # Not needed — uses Gitea

      # ── Logging ──
      LOG_ALL_EVENTS: true
      DEBUG: false
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - openhands_data:/opt/workspace
      - ./config/openhands/config.toml:/app/config.toml:ro
      - ./config/openhands/presets:/app/presets:ro
    depends_on:
      litellm:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 45s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
        reservations:
          memory: 1G
          cpus: "0.5"
    labels:
      - "omni.quantum.component=openhands"
      - "omni.quantum.tier=ai-agents"
      - "omni.quantum.system=18"
      - "prometheus.scrape=true"
      - "prometheus.port=3000"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  openhands_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${DATA_ROOT:-/opt/omni-quantum/data}/openhands

networks:
  omni-quantum-network:
    external: true
```

## CONFIGURATION

```toml
# config/openhands/config.toml
# ═══════════════════════════════════════════════════════════════════════════════
# OPENHANDS — OMNI QUANTUM ELITE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

[core]
workspace_base = "/opt/workspace"
run_as_openhands = true
max_iterations = 100
max_budget_per_task = 0.0
default_agent = "CodeActAgent"
cache_dir = "/tmp/cache"
ssh_hostname = "openhands"

[llm]
model = "litellm/ollama/deepseek-coder-v2"
api_key = "${LITELLM_API_KEY}"
base_url = "http://litellm:4000/v1"
embedding_model = "litellm/ollama/nomic-embed-text"
max_message_chars = 30000
temperature = 0.0
top_p = 0.95
num_retries = 5
retry_min_wait = 3
retry_max_wait = 60
timeout = 600

[llm.fallback]
model = "litellm/groq/llama-3.3-70b-versatile"
api_key = "${LITELLM_API_KEY}"
base_url = "http://litellm:4000/v1"

[sandbox]
type = "docker"
container_image = "docker.all-hands.dev/all-hands-ai/runtime:latest"
user_id = 1000
timeout = 300
enable_auto_lint = true
use_host_network = false
init_plugins = ["JupyterRequirement", "AgentSkillsRequirement"]

[sandbox.resources]
cpus = 2
memory_gb = 4

[security]
enable_security_analyzer = true
confirmation_mode = false
security_analyzer = "invariant"
```

## PYTHON SDK — OPENHANDS INTEGRATION CLIENT

```python
# sdk/openhands_client.py
# ═══════════════════════════════════════════════════════════════════════════════
# OPENHANDS INTEGRATION SDK — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enterprise-grade OpenHands client for the Omni Quantum Elite platform.
Provides programmatic task submission, status monitoring, and result retrieval.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger("omni.quantum.openhands")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentType(Enum):
    CODE_ACT = "CodeActAgent"
    BROWSING = "BrowsingAgent"
    MONOLOGUE = "MonologueAgent"
    DELEGATOR = "DelegatorAgent"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    output: str = ""
    files_modified: list[str] = field(default_factory=list)
    git_diff: str = ""
    iterations_used: int = 0
    cost_estimate: float = 0.0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class OpenHandsClient:
    """Async client for OpenHands AI Coding Agent."""

    def __init__(
        self,
        base_url: str = "http://openhands:3000",
        api_key: Optional[str] = None,
        timeout: int = 600,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(
                headers=headers, timeout=self.timeout
            )
        return self._session

    async def submit_task(
        self,
        instruction: str,
        agent: AgentType = AgentType.CODE_ACT,
        workspace: Optional[str] = None,
        max_iterations: int = 100,
        git_repo: Optional[str] = None,
        git_branch: str = "main",
    ) -> str:
        """Submit a coding task. Returns task_id."""
        session = await self._get_session()
        payload = {
            "instruction": instruction,
            "agent": agent.value,
            "max_iterations": max_iterations,
        }
        if workspace:
            payload["workspace"] = workspace
        if git_repo:
            payload["git_repo"] = git_repo
            payload["git_branch"] = git_branch

        async with session.post(
            f"{self.base_url}/api/conversations", json=payload
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            task_id = data.get("conversation_id", data.get("id"))
            logger.info(f"Task submitted: {task_id}")
            return task_id

    async def get_status(self, task_id: str) -> TaskResult:
        """Get current task status and results."""
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/api/conversations/{task_id}"
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return TaskResult(
                task_id=task_id,
                status=TaskStatus(data.get("status", "pending")),
                output=data.get("output", ""),
                files_modified=data.get("files_modified", []),
                git_diff=data.get("git_diff", ""),
                iterations_used=data.get("iterations", 0),
                duration_seconds=data.get("duration", 0.0),
                error=data.get("error"),
            )

    async def wait_for_completion(
        self, task_id: str, poll_interval: float = 5.0, timeout: float = 3600
    ) -> TaskResult:
        """Poll until task completes or times out."""
        start = asyncio.get_event_loop().time()
        while True:
            result = await self.get_status(task_id)
            if result.status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.TIMEOUT,
                TaskStatus.CANCELLED,
            ):
                return result
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed > timeout:
                result.status = TaskStatus.TIMEOUT
                return result
            await asyncio.sleep(poll_interval)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/conversations/{task_id}/cancel"
        ) as resp:
            return resp.status == 200

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
# scripts/init-openhands.sh
# ═══════════════════════════════════════════════════════════════════════════════
# OPENHANDS INITIALIZATION — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 18: OPENHANDS — AI CODING AGENT"

# Create directories
ensure_dir "${DATA_ROOT}/openhands"
ensure_dir "${CONFIG_ROOT}/openhands/presets"
ensure_dir "${WORKSPACE_ROOT}/openhands"

# Generate secrets
ensure_secret "OPENHANDS_JWT_SECRET" 64

# Pre-pull sandbox runtime image
log_info "Pulling OpenHands sandbox runtime..."
docker pull docker.all-hands.dev/all-hands-ai/runtime:latest 2>/dev/null || true

# Create Gitea webhook preset
cat > "${CONFIG_ROOT}/openhands/presets/gitea-webhook.json" << 'PRESET'
{
  "name": "Gitea PR Review",
  "agent": "CodeActAgent",
  "instruction_template": "Review the pull request at {repo_url}/pulls/{pr_number}. Check for: 1) Code quality and style, 2) Security vulnerabilities, 3) Performance issues, 4) Test coverage. Provide detailed feedback.",
  "max_iterations": 50,
  "triggers": ["pull_request.opened", "pull_request.synchronize"]
}
PRESET

# Create Mattermost integration preset
cat > "${CONFIG_ROOT}/openhands/presets/mattermost-bot.json" << 'PRESET'
{
  "name": "Mattermost Coding Assistant",
  "agent": "CodeActAgent",
  "instruction_template": "User request from Mattermost: {message}. Work in the repository at {workspace_path}. Complete the task and report back.",
  "max_iterations": 100,
  "response_channel": "dev-updates"
}
PRESET

log_success "OpenHands initialized successfully"
log_info "  → Web UI:     http://localhost:3100"
log_info "  → API:        http://openhands:3000/api"
log_info "  → Workspace:  ${WORKSPACE_ROOT}/openhands"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 19: SWE-AGENT — AUTONOMOUS SOFTWARE ENGINEER
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   SWE-AGENT ARCHITECTURE                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ISSUE INPUT                     SWE-AGENT CORE                     OUTPUT                  │
│  ───────────                     ──────────────                     ──────                  │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  🐛 Gitea Issues  │          │                               │  │  📝 Patches       │      │
│  │  • Bug reports    │─────────▶│     AGENT-COMPUTER INTERFACE  │─▶│  • Git commits    │      │
│  │  • Feature reqs   │          │            (ACI)              │  │  • Pull requests  │      │
│  │  • Refactor tasks │          │                               │  │  • Branch pushes  │      │
│  └──────────────────┘          │  ┌─────────┐ ┌─────────────┐ │  └──────────────────┘      │
│                                │  │ SEARCH  │ │ EDIT        │ │                            │
│  ┌──────────────────┐          │  │ • find  │ │ • open      │ │  ┌──────────────────┐      │
│  │  📋 Plane Tasks   │          │  │ • grep  │ │ • edit      │ │  │  📊 Reports       │      │
│  │  • Sprint items   │─────────▶│  │ • tree  │ │ • insert    │ │─▶│  • Success/fail   │      │
│  │  • Auto-assigned  │          │  └─────────┘ │ • replace   │ │  │  • Files changed  │      │
│  └──────────────────┘          │               └─────────────┘ │  │  • Test results   │      │
│                                │  ┌─────────┐ ┌─────────────┐ │  └──────────────────┘      │
│  ┌──────────────────┐          │  │ NAVIGATE│ │ EXECUTE     │ │                            │
│  │  🔄 n8n Workflows │          │  │ • cd    │ │ • bash      │ │  ┌──────────────────┐      │
│  │  • Scheduled runs │─────────▶│  │ • ls    │ │ • python    │ │  │  💬 Mattermost     │      │
│  │  • Event triggers │          │  │ • pwd   │ │ • test      │ │─▶│  • Status updates │      │
│  └──────────────────┘          │  └─────────┘ └─────────────┘ │  │  • PR links       │      │
│                                │                               │  └──────────────────┘      │
│                                │  LLM: LiteLLM → Ollama/Groq  │                            │
│                                └───────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.swe-agent.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # SWE-AGENT — AUTONOMOUS SOFTWARE ENGINEER
  # ═══════════════════════════════════════════════════════════════════════════
  swe-agent:
    build:
      context: ./build/swe-agent
      dockerfile: Dockerfile
    container_name: omni-quantum-swe-agent
    ports:
      - "3101:8000"
    environment:
      # ── LLM (via Token Infinity / LiteLLM) ──
      SWE_AGENT_MODEL: "litellm/ollama/deepseek-coder-v2"
      LITELLM_API_KEY: "${LITELLM_API_KEY}"
      LITELLM_BASE_URL: "http://litellm:4000/v1"

      # ── Repository Access (Gitea) ──
      GITEA_URL: "http://gitea:3000"
      GITEA_TOKEN: "${GITEA_ADMIN_TOKEN}"
      DEFAULT_GIT_USER: "swe-agent"
      DEFAULT_GIT_EMAIL: "swe-agent@omni-quantum.local"

      # ── Execution ──
      MAX_COST: 0           # Unlimited via Token Infinity
      PER_INSTANCE_COST_LIMIT: 0
      TIMEOUT: 600
      MAX_RETRIES: 3

      # ── Observability ──
      LANGFUSE_PUBLIC_KEY: "${LANGFUSE_PUBLIC_KEY}"
      LANGFUSE_SECRET_KEY: "${LANGFUSE_SECRET_KEY}"
      LANGFUSE_HOST: "http://langfuse:3000"

      # ── Database ──
      DATABASE_URL: "postgresql://sweagent:${SWE_AGENT_DB_PASSWORD}@postgres:5432/sweagent"
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/5"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - swe_agent_data:/app/data
      - swe_agent_repos:/app/repos
      - ./config/swe-agent/config.yaml:/app/config.yaml:ro
      - ./config/swe-agent/templates:/app/templates:ro
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
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
        reservations:
          memory: 1G
    labels:
      - "omni.quantum.component=swe-agent"
      - "omni.quantum.tier=ai-agents"
      - "omni.quantum.system=19"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # ═══════════════════════════════════════════════════════════════════════════
  # SWE-AGENT WORKER — Background task processor
  # ═══════════════════════════════════════════════════════════════════════════
  swe-agent-worker:
    build:
      context: ./build/swe-agent
      dockerfile: Dockerfile
    container_name: omni-quantum-swe-agent-worker
    command: ["python", "-m", "celery", "-A", "worker", "worker", "--loglevel=info", "--concurrency=2"]
    environment:
      SWE_AGENT_MODEL: "litellm/ollama/deepseek-coder-v2"
      LITELLM_API_KEY: "${LITELLM_API_KEY}"
      LITELLM_BASE_URL: "http://litellm:4000/v1"
      GITEA_URL: "http://gitea:3000"
      GITEA_TOKEN: "${GITEA_ADMIN_TOKEN}"
      DATABASE_URL: "postgresql://sweagent:${SWE_AGENT_DB_PASSWORD}@postgres:5432/sweagent"
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/5"
      LANGFUSE_PUBLIC_KEY: "${LANGFUSE_PUBLIC_KEY}"
      LANGFUSE_SECRET_KEY: "${LANGFUSE_SECRET_KEY}"
      LANGFUSE_HOST: "http://langfuse:3000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - swe_agent_repos:/app/repos
    depends_on:
      - swe-agent
    networks:
      - omni-quantum-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
    labels:
      - "omni.quantum.component=swe-agent-worker"
      - "omni.quantum.tier=ai-agents"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  swe_agent_data:
    driver: local
  swe_agent_repos:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## BUILD DOCKERFILE

```dockerfile
# build/swe-agent/Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
# SWE-AGENT — CUSTOM BUILD FOR OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl docker.io jq && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install SWE-Agent from source
RUN pip install swe-agent[all] celery[redis] \
    fastapi uvicorn httpx langfuse psycopg2-binary

COPY config.yaml /app/config.yaml
COPY templates/ /app/templates/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## CONFIGURATION

```yaml
# config/swe-agent/config.yaml
# ═══════════════════════════════════════════════════════════════════════════════
# SWE-AGENT CONFIGURATION — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

agent:
  model:
    name: "litellm/ollama/deepseek-coder-v2"
    api_key: "${LITELLM_API_KEY}"
    api_base: "http://litellm:4000/v1"
    temperature: 0.0
    top_p: 0.95
    max_tokens: 4096
    per_instance_cost_limit: 0.0  # Unlimited

  config:
    system_template: |
      You are an autonomous software engineer working on the Omni Quantum Elite platform.
      You have access to a sandboxed environment with bash, git, and development tools.
      Your goal: resolve the assigned issue by producing a working patch.
      Always write tests. Always run tests before submitting.
      Follow the project's coding standards and conventions.

  tools:
    - name: "bash"
      enabled: true
    - name: "edit"
      enabled: true
    - name: "search"
      enabled: true
    - name: "git"
      enabled: true

execution:
  timeout: 600
  max_retries: 3
  sandbox:
    type: "docker"
    image: "python:3.12-slim"
    memory_limit: "2g"
    cpu_limit: 2
    network_mode: "bridge"

integrations:
  gitea:
    url: "http://gitea:3000"
    auto_create_branch: true
    branch_prefix: "swe-agent/"
    auto_create_pr: true
    pr_template: |
      ## Automated Fix by SWE-Agent

      **Issue:** #{issue_number}
      **Status:** {status}

      ### Changes
      {changes_summary}

      ### Test Results
      ```
      {test_output}
      ```

      ---
      _Generated by SWE-Agent • Omni Quantum Elite_

  mattermost:
    webhook_url: "http://mattermost:8065/hooks/${MATTERMOST_SWE_WEBHOOK}"
    channel: "dev-updates"
    notify_on: ["start", "success", "failure"]

  langfuse:
    enabled: true
    trace_name: "swe-agent-run"
    tags: ["autonomous", "coding", "omni-quantum"]
```

## PYTHON SDK — SWE-AGENT CLIENT

```python
# sdk/swe_agent_client.py
# ═══════════════════════════════════════════════════════════════════════════════
# SWE-AGENT INTEGRATION SDK — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enterprise-grade SWE-Agent client for autonomous issue resolution.
Integrates with Gitea, Plane, and the Token Infinity system.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import aiohttp

logger = logging.getLogger("omni.quantum.swe_agent")


class RunStatus(Enum):
    QUEUED = "queued"
    CLONING = "cloning"
    RUNNING = "running"
    TESTING = "testing"
    SUBMITTING = "submitting"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SWERunResult:
    run_id: str
    status: RunStatus
    issue_url: str = ""
    pr_url: str = ""
    patch: str = ""
    files_changed: list[str] = field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    duration_seconds: float = 0.0
    model_used: str = ""
    error: Optional[str] = None


class SWEAgentClient:
    """Async client for SWE-Agent autonomous software engineer."""

    def __init__(
        self,
        base_url: str = "http://swe-agent:8000",
        timeout: int = 900,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        return self._session

    async def resolve_issue(
        self,
        repo_url: str,
        issue_number: int,
        branch: str = "main",
        auto_pr: bool = True,
        max_retries: int = 3,
    ) -> str:
        """Submit an issue for autonomous resolution. Returns run_id."""
        session = await self._get_session()
        payload = {
            "repo_url": repo_url,
            "issue_number": issue_number,
            "base_branch": branch,
            "auto_create_pr": auto_pr,
            "max_retries": max_retries,
        }
        async with session.post(
            f"{self.base_url}/api/runs", json=payload
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            run_id = data["run_id"]
            logger.info(f"SWE-Agent run submitted: {run_id} for issue #{issue_number}")
            return run_id

    async def get_run(self, run_id: str) -> SWERunResult:
        """Get run status and results."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/runs/{run_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return SWERunResult(
                run_id=run_id,
                status=RunStatus(data.get("status", "queued")),
                issue_url=data.get("issue_url", ""),
                pr_url=data.get("pr_url", ""),
                patch=data.get("patch", ""),
                files_changed=data.get("files_changed", []),
                tests_passed=data.get("tests_passed", 0),
                tests_failed=data.get("tests_failed", 0),
                duration_seconds=data.get("duration", 0.0),
                model_used=data.get("model", ""),
                error=data.get("error"),
            )

    async def wait_for_completion(
        self, run_id: str, poll_interval: float = 10.0, timeout: float = 3600
    ) -> SWERunResult:
        """Poll until run completes."""
        start = asyncio.get_event_loop().time()
        while True:
            result = await self.get_run(run_id)
            if result.status in (RunStatus.SUCCESS, RunStatus.FAILED, RunStatus.TIMEOUT):
                return result
            if asyncio.get_event_loop().time() - start > timeout:
                result.status = RunStatus.TIMEOUT
                return result
            await asyncio.sleep(poll_interval)

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
# scripts/init-swe-agent.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 19: SWE-AGENT — AUTONOMOUS SOFTWARE ENGINEER"

ensure_dir "${DATA_ROOT}/swe-agent"
ensure_dir "${CONFIG_ROOT}/swe-agent/templates"
ensure_dir "${BUILD_ROOT}/swe-agent"

ensure_secret "SWE_AGENT_DB_PASSWORD" 32

# Create database
create_postgres_db "sweagent" "sweagent" "${SWE_AGENT_DB_PASSWORD}"

# Create entrypoint
cat > "${BUILD_ROOT}/swe-agent/entrypoint.sh" << 'EOF'
#!/bin/bash
set -e
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  SWE-AGENT — OMNI QUANTUM ELITE                        ║"
echo "║  Autonomous Software Engineer                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
git config --global user.name "${DEFAULT_GIT_USER:-swe-agent}"
git config --global user.email "${DEFAULT_GIT_EMAIL:-swe-agent@omni-quantum.local}"
exec "$@"
EOF
chmod +x "${BUILD_ROOT}/swe-agent/entrypoint.sh"

log_success "SWE-Agent initialized successfully"
log_info "  → API:      http://localhost:3101"
log_info "  → Database: sweagent@postgres"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 20: NANGO — API INTEGRATION PLATFORM
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    NANGO ARCHITECTURE                                        │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  EXTERNAL APIs                   NANGO CORE                         INTERNAL SERVICES       │
│  ─────────────                   ──────────                         ─────────────────       │
│                                                                                             │
│  ┌──────────┐ ┌──────────┐     ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │ GitHub   │ │ Stripe   │     │                               │  │  n8n Workflows   │      │
│  │ Gmail    │ │ Twilio   │     │     CONNECTION MANAGEMENT     │  │  • Sync triggers │      │
│  │ HubSpot  │ │ Jira     │────▶│                               │─▶│  • Data mapping  │      │
│  │ Notion   │ │ Discord  │     │  ┌─────────────────────────┐ │  │  • Error handler │      │
│  │ Linear   │ │ Airtable │     │  │ 250+ Pre-built Providers │ │  └──────────────────┘      │
│  └──────────┘ └──────────┘     │  │ • OAuth 1.0/2.0/2.0c    │ │                            │
│                                │  │ • API Key auth           │ │  ┌──────────────────┐      │
│  ┌─────────────────────────┐   │  │ • Basic auth             │ │  │  Custom Scripts   │      │
│  │  OAUTH FLOW             │   │  │ • Token refresh          │ │  │  • Transform data│      │
│  │                         │   │  └─────────────────────────┘ │─▶│  • Validate       │      │
│  │  User ──▶ Provider ──▶  │   │                               │  │  • Enrich         │      │
│  │  Callback ──▶ Nango ──▶ │   │  ┌─────────────────────────┐ │  └──────────────────┘      │
│  │  Token stored encrypted │   │  │ SYNC ENGINE              │ │                            │
│  │                         │   │  │ • Incremental syncs      │ │  ┌──────────────────┐      │
│  └─────────────────────────┘   │  │ • Full refresh syncs     │ │  │  PostgreSQL       │      │
│                                │  │ • Webhook listeners      │ │─▶│  • Synced records │      │
│                                │  │ • Rate limit handling    │ │  │  • Connection data│      │
│                                │  │ • Auto-pagination        │ │  │  • Audit logs     │      │
│                                │  └─────────────────────────┘ │  └──────────────────┘      │
│                                └───────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.nango.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # NANGO SERVER — API Connection Hub
  # ═══════════════════════════════════════════════════════════════════════════
  nango-server:
    image: nango/nango-server:hosted
    container_name: omni-quantum-nango-server
    ports:
      - "3103:3003"
    environment:
      # ── Database ──
      NANGO_DATABASE_URL: "postgresql://nango:${NANGO_DB_PASSWORD}@postgres:5432/nango"

      # ── Server ──
      NANGO_SERVER_URL: "http://nango-server:3003"
      NANGO_DASHBOARD_URL: "http://localhost:3103"
      SERVER_PORT: 3003
      NANGO_SERVER_WEBSOCKETS_PATH: ""

      # ── Encryption ──
      NANGO_ENCRYPTION_KEY: "${NANGO_ENCRYPTION_KEY}"
      NANGO_SECRET_KEY: "${NANGO_SECRET_KEY}"
      NANGO_SECRET_KEY_IV: "${NANGO_SECRET_KEY_IV}"

      # ── Redis ──
      NANGO_REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/6"

      # ── Auth ──
      NANGO_ADMIN_KEY: "${NANGO_ADMIN_KEY}"

      # ── Logging ──
      LOG_LEVEL: "info"
      TELEMETRY: "false"

      # ── Features ──
      NANGO_MANAGE_CONNECTION_CONFIGS: "true"
      DEFAULT_GITHUB_CLIENT_ID: ""
      DEFAULT_GITHUB_CLIENT_SECRET: ""
    volumes:
      - nango_data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3003/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    labels:
      - "omni.quantum.component=nango-server"
      - "omni.quantum.tier=integrations"
      - "omni.quantum.system=20"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # ═══════════════════════════════════════════════════════════════════════════
  # NANGO RUNNER — Sync Execution Engine
  # ═══════════════════════════════════════════════════════════════════════════
  nango-runner:
    image: nango/nango-runner:hosted
    container_name: omni-quantum-nango-runner
    environment:
      NANGO_DATABASE_URL: "postgresql://nango:${NANGO_DB_PASSWORD}@postgres:5432/nango"
      NANGO_ENCRYPTION_KEY: "${NANGO_ENCRYPTION_KEY}"
      NANGO_REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/6"
      NANGO_SERVER_URL: "http://nango-server:3003"
      LOG_LEVEL: "info"
      TELEMETRY: "false"
    depends_on:
      nango-server:
        condition: service_healthy
    networks:
      - omni-quantum-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    labels:
      - "omni.quantum.component=nango-runner"
      - "omni.quantum.tier=integrations"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  nango_data:
    driver: local

networks:
  omni-quantum-network:
    external: true
```

## PYTHON SDK — NANGO CLIENT

```python
# sdk/nango_client.py
# ═══════════════════════════════════════════════════════════════════════════════
# NANGO INTEGRATION SDK — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

"""
Unified API integration client via Nango.
Manages OAuth connections, syncs, and proxy requests to 250+ providers.
"""

import logging
from typing import Any, Optional

import aiohttp

logger = logging.getLogger("omni.quantum.nango")


class NangoClient:
    """Async client for Nango API Integration Platform."""

    def __init__(
        self,
        base_url: str = "http://nango-server:3003",
        secret_key: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.secret_key = secret_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.secret_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._session

    async def list_connections(self) -> list[dict]:
        """List all active connections."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/connections") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("connections", [])

    async def get_connection(
        self, provider_config_key: str, connection_id: str
    ) -> dict:
        """Get connection details including tokens."""
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/connections/{connection_id}",
            params={"provider_config_key": provider_config_key},
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def proxy_request(
        self,
        method: str,
        endpoint: str,
        provider_config_key: str,
        connection_id: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Proxy an API request through Nango (handles auth automatically)."""
        session = await self._get_session()
        headers = {
            "Provider-Config-Key": provider_config_key,
            "Connection-Id": connection_id,
        }
        async with session.request(
            method,
            f"{self.base_url}/proxy{endpoint}",
            headers=headers,
            json=data,
            params=params,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def trigger_sync(
        self, provider_config_key: str, connection_id: str, sync_name: str
    ) -> dict:
        """Trigger a data sync."""
        session = await self._get_session()
        payload = {
            "provider_config_key": provider_config_key,
            "connection_id": connection_id,
            "sync_name": sync_name,
        }
        async with session.post(
            f"{self.base_url}/syncs/trigger", json=payload
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_records(
        self,
        connection_id: str,
        provider_config_key: str,
        model: str,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """Get synced records."""
        session = await self._get_session()
        params = {
            "model": model,
            "connection_id": connection_id,
            "provider_config_key": provider_config_key,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor
        async with session.get(
            f"{self.base_url}/records", params=params
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
# scripts/init-nango.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 20: NANGO — API INTEGRATION PLATFORM"

ensure_dir "${DATA_ROOT}/nango"
ensure_dir "${CONFIG_ROOT}/nango"

ensure_secret "NANGO_DB_PASSWORD" 32
ensure_secret "NANGO_ENCRYPTION_KEY" 32
ensure_secret "NANGO_SECRET_KEY" 64
ensure_secret "NANGO_SECRET_KEY_IV" 16
ensure_secret "NANGO_ADMIN_KEY" 48

create_postgres_db "nango" "nango" "${NANGO_DB_PASSWORD}"

log_success "Nango initialized successfully"
log_info "  → Dashboard: http://localhost:3103"
log_info "  → API:       http://nango-server:3003"
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM 21: MINIO — S3-COMPATIBLE OBJECT STORAGE
# ══════════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     MINIO ARCHITECTURE                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  CLIENTS                         MINIO CLUSTER                      STORAGE TIERS           │
│  ───────                         ─────────────                      ─────────────           │
│                                                                                             │
│  ┌──────────────────┐          ┌───────────────────────────────┐  ┌──────────────────┐      │
│  │  📦 S3 API        │          │                               │  │  🔥 HOT TIER      │      │
│  │  • AWS SDK        │─────────▶│     MINIO GATEWAY             │  │  • NVMe/SSD       │      │
│  │  • mc CLI         │          │                               │  │  • Frequent access │      │
│  │  • rclone         │          │  ┌─────────────────────────┐ │  └──────────────────┘      │
│  └──────────────────┘          │  │ LOAD BALANCER            │ │                            │
│                                │  │ (Built-in / Traefik)     │ │  ┌──────────────────┐      │
│  ┌──────────────────┐          │  └─────────────────────────┘ │  │  ❄️ COLD TIER      │      │
│  │  🧠 AI Services   │          │          │         │          │  │  • HDD             │      │
│  │  • Model weights  │─────────▶│  ┌───────┴───┐ ┌──┴────────┐│  │  • Archives        │      │
│  │  • Training data  │          │  │ MINIO     │ │ MINIO     ││  └──────────────────┘      │
│  │  • Embeddings     │          │  │ NODE 1    │ │ NODE 2    ││                            │
│  └──────────────────┘          │  │ (Primary) │ │ (Standby) ││                            │
│                                │  └───────────┘ └───────────┘│                            │
│  ┌──────────────────┐          │                               │  ┌──────────────────┐      │
│  │  💾 Backups       │          │  FEATURES:                    │  │  BUCKETS:          │      │
│  │  • DB snapshots   │─────────▶│  • Erasure coding (EC:4)     │  │  • models          │      │
│  │  • Config exports │          │  • Bitrot protection          │  │  • datasets        │      │
│  │  • Git bundles    │          │  • Versioning + Locking      │  │  • backups         │      │
│  └──────────────────┘          │  • Bucket notifications       │  │  • artifacts       │      │
│                                │  • S3 Select queries          │  │  • uploads         │      │
│  ┌──────────────────┐          │  • Object lifecycle           │  │  • logs            │      │
│  │  📊 Analytics     │          │  • Replication                │  │  • training-data   │      │
│  │  • Data lakes     │─────────▶│  • Prometheus metrics         │  │  • embeddings      │      │
│  │  • CSV/Parquet    │          │  • Audit logging              │  └──────────────────┘      │
│  └──────────────────┘          └───────────────────────────────┘                            │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE

```yaml
# docker-compose.minio.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════
  # MINIO — S3-Compatible Object Storage
  # ═══════════════════════════════════════════════════════════════════════════
  minio:
    image: quay.io/minio/minio:latest
    container_name: omni-quantum-minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"     # S3 API
      - "9001:9001"     # Web Console
    environment:
      MINIO_ROOT_USER: "${MINIO_ROOT_USER}"
      MINIO_ROOT_PASSWORD: "${MINIO_ROOT_PASSWORD}"

      # ── Identity & Access ──
      MINIO_BROWSER: "on"
      MINIO_BROWSER_REDIRECT_URL: "http://localhost:9001"

      # ── Region ──
      MINIO_SITE_REGION: "us-east-1"
      MINIO_SITE_NAME: "omni-quantum"

      # ── Monitoring ──
      MINIO_PROMETHEUS_AUTH_TYPE: "public"
      MINIO_PROMETHEUS_URL: "http://prometheus:9090"
      MINIO_PROMETHEUS_JOB_ID: "minio-metrics"

      # ── Notifications (Mattermost via webhook) ──
      MINIO_NOTIFY_WEBHOOK_ENABLE_PRIMARY: "on"
      MINIO_NOTIFY_WEBHOOK_ENDPOINT_PRIMARY: "http://n8n:5678/webhook/minio-events"
      MINIO_NOTIFY_WEBHOOK_QUEUE_DIR_PRIMARY: "/data/.minio/events"

      # ── Logging ──
      MINIO_AUDIT_WEBHOOK_ENABLE: "on"
      MINIO_AUDIT_WEBHOOK_ENDPOINT: "http://n8n:5678/webhook/minio-audit"

      # ── Healing ──
      MINIO_HEAL_INTERVAL: "30m"

      # ── Compression ──
      MINIO_COMPRESSION_ENABLE: "on"
      MINIO_COMPRESSION_EXTENSIONS: ".txt,.log,.csv,.json,.xml,.html,.md,.yaml,.yml"
      MINIO_COMPRESSION_MIME_TYPES: "text/*,application/json,application/xml"
    volumes:
      - minio_data:/data
      - ./config/minio/certs:/root/.minio/certs:ro
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
        reservations:
          memory: 512M
    labels:
      - "omni.quantum.component=minio"
      - "omni.quantum.tier=storage"
      - "omni.quantum.system=21"
      - "prometheus.scrape=true"
      - "prometheus.port=9000"
      - "prometheus.path=/minio/v2/metrics/cluster"
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # ═══════════════════════════════════════════════════════════════════════════
  # MINIO CLIENT — Initialization & Management
  # ═══════════════════════════════════════════════════════════════════════════
  minio-init:
    image: quay.io/minio/mc:latest
    container_name: omni-quantum-minio-init
    entrypoint: /bin/sh
    command: |
      -c '
      echo "═══════════════════════════════════════════════"
      echo "  MINIO BUCKET INITIALIZATION"
      echo "═══════════════════════════════════════════════"

      # Wait for MinIO
      until mc alias set oqe http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 2>/dev/null; do
        echo "Waiting for MinIO..."
        sleep 3
      done

      # Create core buckets
      BUCKETS="models datasets backups artifacts uploads logs training-data embeddings documents temp"
      for bucket in $BUCKETS; do
        mc mb --ignore-existing oqe/$bucket
        echo "  ✓ Bucket: $bucket"
      done

      # Set lifecycle policies
      mc ilm rule add oqe/temp --expire-days 7 --noncurrent-expire-days 1
      mc ilm rule add oqe/logs --expire-days 90 --noncurrent-expire-days 30
      mc ilm rule add oqe/backups --noncurrent-expire-days 30

      # Enable versioning on critical buckets
      mc version enable oqe/models
      mc version enable oqe/backups
      mc version enable oqe/documents

      # Set public read on artifacts (for CI/CD downloads)
      mc anonymous set download oqe/artifacts

      # Create service accounts
      mc admin user add oqe ai-service "${MINIO_AI_PASSWORD}" 2>/dev/null || true
      mc admin user add oqe backup-service "${MINIO_BACKUP_PASSWORD}" 2>/dev/null || true

      # Apply policies
      mc admin policy attach oqe readwrite --user ai-service
      mc admin policy attach oqe readwrite --user backup-service

      # Set bucket notifications for n8n webhooks
      mc event add oqe/uploads arn:minio:sqs::PRIMARY:webhook --event put,delete

      echo "═══════════════════════════════════════════════"
      echo "  ✅ MINIO INITIALIZATION COMPLETE"
      echo "═══════════════════════════════════════════════"
      '
    environment:
      MINIO_ROOT_USER: "${MINIO_ROOT_USER}"
      MINIO_ROOT_PASSWORD: "${MINIO_ROOT_PASSWORD}"
      MINIO_AI_PASSWORD: "${MINIO_AI_PASSWORD}"
      MINIO_BACKUP_PASSWORD: "${MINIO_BACKUP_PASSWORD}"
    depends_on:
      minio:
        condition: service_healthy
    networks:
      - omni-quantum-network

volumes:
  minio_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${DATA_ROOT:-/opt/omni-quantum/data}/minio

networks:
  omni-quantum-network:
    external: true
```

## PYTHON SDK — MINIO CLIENT

```python
# sdk/minio_client.py
# ═══════════════════════════════════════════════════════════════════════════════
# MINIO S3 STORAGE SDK — OMNI QUANTUM ELITE
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enterprise S3-compatible storage client with bucket management,
presigned URLs, multipart uploads, and lifecycle automation.
"""

import io
import json
import logging
from datetime import timedelta
from typing import Any, BinaryIO, Iterator, Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger("omni.quantum.minio")


class OQEStorageClient:
    """Unified S3 storage client for Omni Quantum Elite."""

    # Pre-defined bucket registry
    BUCKETS = {
        "models": "AI model weights and checkpoints",
        "datasets": "Training and evaluation datasets",
        "backups": "System backups and snapshots",
        "artifacts": "Build artifacts and releases",
        "uploads": "User uploads and attachments",
        "logs": "Application and audit logs",
        "training-data": "ML training data pipelines",
        "embeddings": "Vector embeddings cache",
        "documents": "Documents and reports",
        "temp": "Temporary files (auto-expire 7d)",
    }

    def __init__(
        self,
        endpoint: str = "minio:9000",
        access_key: str = "",
        secret_key: str = "",
        secure: bool = False,
        region: str = "us-east-1",
    ):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> str:
        """Upload a file to a bucket. Returns the object URL."""
        self.client.fput_object(
            bucket,
            object_name,
            file_path,
            content_type=content_type,
            metadata=metadata,
        )
        logger.info(f"Uploaded {object_name} to {bucket}")
        return f"s3://{bucket}/{object_name}"

    def upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> str:
        """Upload bytes directly to a bucket."""
        stream = io.BytesIO(data)
        self.client.put_object(
            bucket,
            object_name,
            stream,
            length=len(data),
            content_type=content_type,
            metadata=metadata,
        )
        return f"s3://{bucket}/{object_name}"

    def download_file(self, bucket: str, object_name: str, file_path: str) -> str:
        """Download an object to a local file."""
        self.client.fget_object(bucket, object_name, file_path)
        return file_path

    def get_bytes(self, bucket: str, object_name: str) -> bytes:
        """Download object as bytes."""
        response = self.client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access."""
        if method == "PUT":
            return self.client.presigned_put_object(bucket, object_name, expires)
        return self.client.presigned_get_object(bucket, object_name, expires)

    def list_objects(
        self, bucket: str, prefix: str = "", recursive: bool = True
    ) -> Iterator[dict]:
        """List objects in a bucket with optional prefix filter."""
        for obj in self.client.list_objects(bucket, prefix=prefix, recursive=recursive):
            yield {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
                "etag": obj.etag,
                "content_type": obj.content_type,
            }

    def delete_object(self, bucket: str, object_name: str) -> None:
        """Delete a single object."""
        self.client.remove_object(bucket, object_name)
        logger.info(f"Deleted {object_name} from {bucket}")

    def upload_json(
        self, bucket: str, object_name: str, data: Any, metadata: Optional[dict] = None
    ) -> str:
        """Convenience: upload a JSON-serializable object."""
        json_bytes = json.dumps(data, default=str, indent=2).encode("utf-8")
        return self.upload_bytes(
            bucket, object_name, json_bytes,
            content_type="application/json", metadata=metadata,
        )

    def download_json(self, bucket: str, object_name: str) -> Any:
        """Convenience: download and parse a JSON object."""
        return json.loads(self.get_bytes(bucket, object_name))

    def get_bucket_size(self, bucket: str) -> dict:
        """Calculate total bucket size and object count."""
        total_size = 0
        total_objects = 0
        for obj in self.client.list_objects(bucket, recursive=True):
            total_size += obj.size or 0
            total_objects += 1
        return {
            "bucket": bucket,
            "total_size_bytes": total_size,
            "total_size_human": self._human_size(total_size),
            "total_objects": total_objects,
        }

    @staticmethod
    def _human_size(num: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(num) < 1024.0:
                return f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} PB"
```

## INIT SCRIPT

```bash
#!/usr/bin/env bash
# scripts/init-minio.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_header "SYSTEM 21: MINIO — S3-COMPATIBLE OBJECT STORAGE"

ensure_dir "${DATA_ROOT}/minio"
ensure_dir "${CONFIG_ROOT}/minio/certs"

ensure_secret "MINIO_ROOT_USER" 20
ensure_secret "MINIO_ROOT_PASSWORD" 40
ensure_secret "MINIO_AI_PASSWORD" 32
ensure_secret "MINIO_BACKUP_PASSWORD" 32

log_success "MinIO initialized successfully"
log_info "  → S3 API:    http://localhost:9000"
log_info "  → Console:   http://localhost:9001"
log_info "  → Buckets:   models, datasets, backups, artifacts, uploads, logs, training-data, embeddings, documents, temp"
```
