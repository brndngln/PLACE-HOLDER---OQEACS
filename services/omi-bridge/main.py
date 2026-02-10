#!/usr/bin/env python3
"""
SYSTEM 28 — OMI WEARABLE BRIDGE: Main Application
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

FastAPI + WebSocket service (port 9700) connecting Omi wearable devices
to the Omni Quantum platform.  Provides haptic feedback, voice command
processing via LiteLLM, and device status monitoring.

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client, pyyaml, websockets
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
import uvicorn
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger(service="omi-bridge", system="28", component="omi-bridge")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LITELLM_URL = os.environ.get("LITELLM_URL", "http://omni-litellm:4000")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
OMI_DEVICE_TOKEN = os.environ.get("OMI_DEVICE_TOKEN", "")
MATTERMOST_WEBHOOK_URL = os.environ.get("MATTERMOST_WEBHOOK_URL", "")
VOICE_COMMANDS_PATH = Path(os.environ.get(
    "VOICE_COMMANDS_PATH",
    str(Path(__file__).resolve().parent / "config" / "voice-commands.yaml"),
))
HEARTBEAT_INTERVAL = 30  # seconds

# ---------------------------------------------------------------------------
# Haptic patterns (vibration durations in ms)
# ---------------------------------------------------------------------------
HAPTIC_PATTERNS: dict[str, list[int]] = {
    "critical": [200, 100, 200, 100, 200, 100, 500],
    "warning": [300, 200, 300],
    "info": [100],
    "build-complete": [200, 100, 200],
    "deploy-success": [100, 50, 100, 50, 100],
    "test-failure": [100, 50, 100, 50, 100, 50, 100, 50, 100],
}

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
OMI_COMMANDS = Counter("omi_commands_total", "Voice commands processed", ["intent"])
OMI_COMMAND_LATENCY = Histogram("omi_command_latency_seconds", "Voice command processing latency")
OMI_DEVICE_CONNECTED = Gauge("omi_device_connected", "Whether an Omi device is connected")
OMI_HAPTIC_SENT = Counter("omi_haptic_sent_total", "Haptic notifications sent", ["pattern"])

# ---------------------------------------------------------------------------
# Device state
# ---------------------------------------------------------------------------
device_state: dict[str, Any] = {
    "connected": False,
    "battery": None,
    "last_seen": None,
    "firmware": None,
}
_active_websocket: WebSocket | None = None

# ---------------------------------------------------------------------------
# Voice command config
# ---------------------------------------------------------------------------
_voice_config: dict[str, Any] = {}


def load_voice_commands() -> dict[str, Any]:
    """Load voice command configuration from YAML."""
    global _voice_config
    if not _voice_config and VOICE_COMMANDS_PATH.exists():
        with open(VOICE_COMMANDS_PATH) as fh:
            _voice_config = yaml.safe_load(fh) or {}
        log.info("voice_commands_loaded", count=len(_voice_config.get("commands", {})))
    return _voice_config


# ---------------------------------------------------------------------------
# LiteLLM helpers
# ---------------------------------------------------------------------------
async def parse_intent(client: httpx.AsyncClient, text: str) -> dict[str, Any]:
    """Use LiteLLM to parse a voice command into a structured intent."""
    config = load_voice_commands()
    commands_desc = ""
    for cmd_name, cmd_info in config.get("commands", {}).items():
        examples = ", ".join(cmd_info.get("examples", []))
        commands_desc += f"- {cmd_name}: {examples}\n"

    system_prompt = (
        "You are a voice command parser for the Omni Quantum platform. "
        "Parse the user's spoken text into a JSON object with 'intent' and 'parameters'.\n"
        "Valid intents:\n" + commands_desc + "\n"
        "If the command does not match any intent, use 'unknown'.\n"
        "Always respond with valid JSON only: {\"intent\": \"...\", \"parameters\": {...}}"
    )

    try:
        resp = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        log.error("intent_parse_failed", text=text, error=str(exc))
        return {"intent": "unknown", "parameters": {}}


async def generate_tts_response(client: httpx.AsyncClient, text: str) -> str:
    """Generate a concise spoken response via LiteLLM."""
    try:
        resp = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise voice assistant for the Omni Quantum platform. "
                        "Keep responses under 2 sentences. Be direct and informative.",
                    },
                    {"role": "user", "content": f"Summarize this for speech: {text}"},
                ],
                "temperature": 0.3,
                "max_tokens": 100,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        log.warning("tts_generation_failed", error=str(exc))
        return text[:200]


# ---------------------------------------------------------------------------
# Orchestrator command execution
# ---------------------------------------------------------------------------
INTENT_TO_ORCHESTRATOR: dict[str, dict[str, str]] = {
    "check_status": {"method": "GET", "path": "/api/services"},
    "restart_service": {"method": "POST", "path": "/api/services/{service_name}/restart"},
    "trigger_backup": {"method": "POST", "path": "/api/backup/trigger"},
    "deploy_app": {"method": "POST", "path": "/api/deploy/{app_name}"},
    "get_build_status": {"method": "GET", "path": "/api/pipeline/status"},
    "get_costs": {"method": "GET", "path": "/api/costs/today"},
    "get_health": {"method": "GET", "path": "/api/services/{service_name}/health"},
    "list_services": {"method": "GET", "path": "/api/services"},
    "search_knowledge": {"method": "GET", "path": "/api/knowledge/search"},
}


async def execute_command(
    client: httpx.AsyncClient,
    intent: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Execute a voice command by calling the Orchestrator API."""
    mapping = INTENT_TO_ORCHESTRATOR.get(intent)
    if not mapping:
        return {"error": f"Unknown intent: {intent}", "valid_commands": list(INTENT_TO_ORCHESTRATOR.keys())}

    config = load_voice_commands()
    cmd_config = config.get("commands", {}).get(intent, {})
    if cmd_config.get("confirm") and not parameters.get("confirmed"):
        return {"requires_confirmation": True, "intent": intent, "message": f"Are you sure you want to {intent.replace('_', ' ')}?"}

    path = mapping["path"]
    for param_key, param_val in parameters.items():
        path = path.replace(f"{{{param_key}}}", str(param_val))

    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.request(
                mapping["method"],
                f"{ORCHESTRATOR_URL}{path}",
                params=parameters if mapping["method"] == "GET" else None,
                json=parameters if mapping["method"] == "POST" else None,
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500 and attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return {"error": f"Orchestrator returned {exc.response.status_code}", "detail": exc.response.text[:500]}
        except httpx.TransportError as exc:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return {"error": f"Connection to Orchestrator failed: {exc}"}

    return {"error": "Max retries exceeded"}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_voice_commands()
    OMI_DEVICE_CONNECTED.set(0)
    log.info("startup_complete")
    yield
    log.info("shutdown")


app = FastAPI(
    title="Omni Quantum Omi Wearable Bridge",
    version="1.0.0",
    description="System 28 — Omi Wearable Bridge",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware — request metrics
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Health / Ready / Metrics
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "omi-bridge", "system": "28"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness probe."""
    return {"status": "ready", "device_connected": device_state["connected"]}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# REST: Haptic
# ---------------------------------------------------------------------------
@app.post("/api/haptic")
async def send_haptic(request: Request) -> dict[str, Any]:
    """Send a haptic pattern to the connected Omi device.

    Body:
        pattern: Haptic pattern name (critical, warning, info, build-complete, deploy-success, test-failure)
        message: Optional text description
    """
    body = await request.json()
    pattern_name = body.get("pattern", "info")
    message = body.get("message")

    sequence = HAPTIC_PATTERNS.get(pattern_name)
    if not sequence:
        return {"error": f"Unknown pattern: {pattern_name}", "valid_patterns": list(HAPTIC_PATTERNS.keys())}

    OMI_HAPTIC_SENT.labels(pattern=pattern_name).inc()

    # Send to connected WebSocket device
    global _active_websocket
    if _active_websocket:
        try:
            await _active_websocket.send_json({
                "type": "haptic",
                "pattern": pattern_name,
                "sequence": sequence,
                "message": message,
            })
            log.info("haptic_sent", pattern=pattern_name, message=message)
            return {"status": "sent", "pattern": pattern_name, "sequence": sequence}
        except Exception as exc:
            log.warning("haptic_send_failed", pattern=pattern_name, error=str(exc))
            return {"status": "device_disconnected", "pattern": pattern_name, "queued": True}
    else:
        log.info("haptic_queued_no_device", pattern=pattern_name)
        return {"status": "no_device", "pattern": pattern_name, "queued": True}


# ---------------------------------------------------------------------------
# REST: Voice command
# ---------------------------------------------------------------------------
@app.post("/api/voice/command")
async def process_voice_command(request: Request) -> dict[str, Any]:
    """Process a voice command text and return the result.

    Body:
        text: Transcribed voice command text
        confirmed: Optional boolean for commands requiring confirmation
    """
    start = time.monotonic()
    body = await request.json()
    text = body.get("text", "")
    confirmed = body.get("confirmed", False)

    if not text.strip():
        return {"error": "Empty command text"}

    async with httpx.AsyncClient() as client:
        # Parse intent
        parsed = await parse_intent(client, text)
        intent = parsed.get("intent", "unknown")
        parameters = parsed.get("parameters", {})
        if confirmed:
            parameters["confirmed"] = True

        OMI_COMMANDS.labels(intent=intent).inc()

        if intent == "unknown":
            valid = list(INTENT_TO_ORCHESTRATOR.keys())
            result = {
                "intent": "unknown",
                "message": "I didn't understand that command.",
                "valid_commands": valid,
            }
        else:
            result = await execute_command(client, intent, parameters)
            result["intent"] = intent

        # Generate spoken response
        spoken = await generate_tts_response(client, json.dumps(result, default=str)[:500])
        result["spoken_response"] = spoken

        # Haptic feedback
        haptic = "info"
        if result.get("error"):
            haptic = "warning"
        elif intent in ("deploy_app", "restart_service"):
            haptic = "deploy-success" if not result.get("error") else "test-failure"

        if _active_websocket:
            try:
                await _active_websocket.send_json({
                    "type": "haptic",
                    "pattern": haptic,
                    "sequence": HAPTIC_PATTERNS.get(haptic, [100]),
                })
            except Exception:
                pass

    latency = time.monotonic() - start
    OMI_COMMAND_LATENCY.observe(latency)
    log.info("voice_command_processed", text=text, intent=intent, latency_s=round(latency, 3))
    return result


# ---------------------------------------------------------------------------
# REST: Device status
# ---------------------------------------------------------------------------
@app.get("/api/device/status")
async def get_device_status() -> dict[str, Any]:
    """Return the current Omi device connection status."""
    return {
        "connected": device_state["connected"],
        "battery": device_state["battery"],
        "last_seen": device_state["last_seen"],
        "firmware": device_state["firmware"],
    }


# ---------------------------------------------------------------------------
# WebSocket: Device connection
# ---------------------------------------------------------------------------
@app.websocket("/ws/device")
async def websocket_device(ws: WebSocket) -> None:
    """Persistent Omi device WebSocket with heartbeat and auto-reconnect support.

    Messages from device:
        - {"type": "heartbeat", "battery": int, "firmware": str}
        - {"type": "voice_audio", "audio_base64": str}  (transcribed via Whisper/LiteLLM)
        - {"type": "status", ...}

    Messages to device:
        - {"type": "haptic", "pattern": str, "sequence": list[int]}
        - {"type": "voice_response", "text": str}
    """
    global _active_websocket
    await ws.accept()
    _active_websocket = ws
    device_state["connected"] = True
    device_state["last_seen"] = datetime.now(tz=timezone.utc).isoformat()
    OMI_DEVICE_CONNECTED.set(1)
    log.info("device_connected")

    heartbeat_task: asyncio.Task[None] | None = None

    async def send_heartbeat() -> None:
        """Periodically ping the device."""
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await ws.send_json({"type": "ping"})
            except Exception:
                break

    try:
        heartbeat_task = asyncio.create_task(send_heartbeat())

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")
            device_state["last_seen"] = datetime.now(tz=timezone.utc).isoformat()

            if msg_type == "heartbeat":
                device_state["battery"] = data.get("battery")
                device_state["firmware"] = data.get("firmware")
                await ws.send_json({"type": "pong"})

            elif msg_type == "voice_audio":
                # Transcribe via LiteLLM / Whisper endpoint
                async with httpx.AsyncClient() as client:
                    try:
                        transcript_resp = await client.post(
                            f"{LITELLM_URL}/v1/audio/transcriptions",
                            files={"file": ("audio.wav", __import__("base64").b64decode(data.get("audio_base64", "")), "audio/wav")},
                            data={"model": "whisper-1"},
                            timeout=30.0,
                        )
                        transcript_resp.raise_for_status()
                        transcribed_text = transcript_resp.json().get("text", "")
                    except Exception as exc:
                        log.error("transcription_failed", error=str(exc))
                        await ws.send_json({"type": "error", "message": "Transcription failed"})
                        continue

                    if transcribed_text.strip():
                        parsed = await parse_intent(client, transcribed_text)
                        intent = parsed.get("intent", "unknown")
                        parameters = parsed.get("parameters", {})
                        OMI_COMMANDS.labels(intent=intent).inc()

                        if intent == "unknown":
                            result = {"message": "I didn't understand that command.", "valid_commands": list(INTENT_TO_ORCHESTRATOR.keys())}
                        else:
                            result = await execute_command(client, intent, parameters)

                        spoken = await generate_tts_response(client, json.dumps(result, default=str)[:500])
                        await ws.send_json({"type": "voice_response", "text": spoken, "result": result})

                        # Haptic
                        haptic = "info" if not result.get("error") else "warning"
                        await ws.send_json({"type": "haptic", "pattern": haptic, "sequence": HAPTIC_PATTERNS.get(haptic, [100])})

            elif msg_type == "status":
                device_state.update({k: v for k, v in data.items() if k != "type"})

            else:
                log.debug("unknown_ws_message", msg_type=msg_type)

    except WebSocketDisconnect:
        log.info("device_disconnected")
    except Exception as exc:
        log.error("websocket_error", error=str(exc))
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        _active_websocket = None
        device_state["connected"] = False
        OMI_DEVICE_CONNECTED.set(0)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9700, log_level="info")
