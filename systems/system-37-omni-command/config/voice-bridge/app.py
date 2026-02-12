"""
Omni Quantum Elite — Voice Bridge
===================================
Receives voice transcripts from Omi wearable, uses LiteLLM to parse
intent, then executes orchestrator actions.

POST /voice/command — { "transcript": "check the status of vault" }
POST /voice/webhook — Omi webhook endpoint
"""

import json
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
LITELLM_URL = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK", "")
PORT = int(os.getenv("VOICE_BRIDGE_PORT", "9502"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omni-voice-bridge")

app = FastAPI(title="Omni Command Voice Bridge")

INTENT_SYSTEM_PROMPT = """You are the Omni Command voice assistant. Parse the user's voice command
into a structured JSON action for the platform orchestrator.

Available actions:
- {"action": "status"} — get platform overview
- {"action": "health", "target": "<service_codename>"} — check specific service
- {"action": "restart", "target": "<service_codename>"} — restart a service
- {"action": "backup", "target": "<service_codename|all>"} — trigger backup
- {"action": "deploy", "target": "<app_name>"} — trigger deployment
- {"action": "rotate", "target": "<service_codename|all>"} — rotate secrets
- {"action": "search", "query": "<search_term>"} — search services
- {"action": "docker"} — docker stats

Service codenames include: vault, litellm, authentik, prometheus, loki, gitea,
ollama, n8n, mattermost, qdrant, minio, langfuse, plane, nango, openhands,
swe-agent, coolify, flowise, wikijs, superset, calcom, twenty, crater,
crowdsec, portainer, token-infinity, omi-bridge, enhanced-monitoring,
enhanced-logging, uptime-monitor, enhanced-backup, enhanced-secrets,
enhanced-proxy, cicd-pipelines, dev-environments.

Respond ONLY with valid JSON. No explanation."""


class VoiceCommand(BaseModel):
    transcript: str


class OmiWebhook(BaseModel):
    transcript: str | None = None
    text: str | None = None
    event: str | None = None


async def parse_intent(transcript: str) -> dict:
    """Use LiteLLM to parse voice transcript into structured intent."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json={
                    "model": "omni-fast",
                    "messages": [
                        {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                        {"role": "user", "content": transcript},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Strip markdown code blocks if present
            content = content.strip().strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()
            return json.loads(content)
    except Exception as e:
        logger.error(f"Intent parsing failed: {e}")
        return {"action": "status"}  # safe fallback


async def execute_intent(intent: dict) -> str:
    """Execute parsed intent against orchestrator API."""
    action = intent.get("action", "status")
    target = intent.get("target")
    query = intent.get("query")

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            if action == "status":
                resp = await c.get(f"{ORCHESTRATOR_URL}/api/v1/overview")
                data = resp.json()
                return (
                    f"{data.get('emoji', '')} Platform is {data.get('platform_status', 'unknown')}. "
                    f"{data.get('healthy', 0)} of {data.get('total_services', 36)} services healthy. "
                    f"Uptime {data.get('uptime_pct', 0)} percent."
                )

            elif action == "health" and target:
                resp = await c.get(f"{ORCHESTRATOR_URL}/api/v1/status/name/{target}")
                data = resp.json()
                return f"{data.get('name', target)} is {data.get('status', 'unknown')}. Latency {data.get('latency_ms', 0)} milliseconds."

            elif action == "restart" and target:
                resp = await c.post(f"{ORCHESTRATOR_URL}/api/v1/action/restart", json={"target": target})
                return f"Restarting {target}."

            elif action == "backup":
                resp = await c.post(f"{ORCHESTRATOR_URL}/api/v1/action/backup", json={"target": target or "all"})
                return f"Backup triggered for {target or 'all services'}."

            elif action == "deploy" and target:
                resp = await c.post(f"{ORCHESTRATOR_URL}/api/v1/action/deploy", json={"target": target})
                return f"Deploying {target}."

            elif action == "rotate":
                resp = await c.post(f"{ORCHESTRATOR_URL}/api/v1/action/rotate-secrets", json={"target": target or "all"})
                return f"Secret rotation triggered for {target or 'all services'}."

            elif action == "search" and query:
                resp = await c.get(f"{ORCHESTRATOR_URL}/api/v1/search?q={query}")
                data = resp.json()
                results = data.get("results", [])
                if results:
                    names = ", ".join(r["name"] for r in results[:5])
                    return f"Found {len(results)} services matching {query}: {names}."
                return f"No services found matching {query}."

            elif action == "docker":
                resp = await c.get(f"{ORCHESTRATOR_URL}/api/v1/docker/stats")
                data = resp.json()
                return (
                    f"Docker host has {data.get('containers_running', 0)} containers running "
                    f"on {data.get('cpu_count', 0)} CPUs with {data.get('memory_gb', 0)} gigabytes of memory."
                )

            else:
                return "I didn't understand that command. Try asking about platform status, a service health check, or a restart."

    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return f"Sorry, I encountered an error: {str(e)[:80]}"


async def send_to_omi(message: str):
    """Send response back to Omi wearable."""
    if not OMI_WEBHOOK:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(OMI_WEBHOOK, json={"message": message, "source": "omni-command"})
    except Exception as e:
        logger.error(f"Omi webhook failed: {e}")


@app.post("/voice/command")
async def voice_command(cmd: VoiceCommand):
    """Process a voice command from any source."""
    logger.info(f"Voice command: {cmd.transcript}")
    intent = await parse_intent(cmd.transcript)
    logger.info(f"Parsed intent: {intent}")
    response = await execute_intent(intent)
    logger.info(f"Response: {response}")

    await send_to_omi(response)

    return {"transcript": cmd.transcript, "intent": intent, "response": response}


@app.post("/voice/webhook")
async def omi_webhook(payload: OmiWebhook):
    """Omi wearable webhook endpoint."""
    transcript = payload.transcript or payload.text or ""
    if not transcript:
        return {"status": "no_transcript"}

    logger.info(f"Omi webhook: {transcript}")
    intent = await parse_intent(transcript)
    response = await execute_intent(intent)

    await send_to_omi(response)

    return {"transcript": transcript, "intent": intent, "response": response}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "omni-voice-bridge"}
