"""
Omni Quantum Elite — Mattermost ChatOps Bot
============================================
Control the entire platform through Mattermost chat.

Commands:
  !omni status           — Platform overview
  !omni services         — List all services with status
  !omni health <service> — Check specific service
  !omni restart <svc>    — Restart a service container
  !omni backup [svc]     — Trigger backup
  !omni deploy <app>     — Trigger deployment
  !omni rotate [svc]     — Rotate secrets
  !omni search <query>   — Search services
  !omni docker           — Docker host stats
  !omni help             — Show commands
"""

import asyncio
import json
import logging
import os
import time

import httpx
from mattermostdriver import Driver

# Config
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
MATTERMOST_URL = os.getenv("MATTERMOST_URL", "http://omni-mattermost:8065")
MATTERMOST_TOKEN = os.getenv("MATTERMOST_TOKEN", "")
BOT_CHANNEL = os.getenv("BOT_CHANNEL", "omni-control")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("omni-bot")

# Mattermost driver
mm = Driver({
    "url": MATTERMOST_URL.replace("http://", "").replace("https://", "").split(":")[0],
    "port": int(MATTERMOST_URL.split(":")[-1]) if ":" in MATTERMOST_URL.split("//")[-1] else 8065,
    "token": MATTERMOST_TOKEN,
    "scheme": "https" if "https" in MATTERMOST_URL else "http",
    "verify": False,
})


def api_get(path: str) -> dict:
    """Synchronous GET to orchestrator."""
    try:
        with httpx.Client(timeout=15) as c:
            resp = c.get(f"{ORCHESTRATOR_URL}{path}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


def api_post(path: str, data: dict | None = None) -> dict:
    """Synchronous POST to orchestrator."""
    try:
        with httpx.Client(timeout=30) as c:
            resp = c.post(f"{ORCHESTRATOR_URL}{path}", json=data or {})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


def handle_status() -> str:
    data = api_get("/api/v1/overview")
    if "error" in data:
        return f"❌ Failed to get status: {data['error']}"

    emoji = data.get("emoji", "⚪")
    status = data.get("platform_status", "unknown").upper()
    healthy = data.get("healthy", 0)
    total = data.get("total_services", 36)
    degraded = data.get("degraded", 0)
    down = data.get("down", 0)
    uptime = data.get("uptime_pct", 0)

    lines = [
        f"## {emoji} Platform Status: **{status}**",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Services Healthy | **{healthy}/{total}** |",
        f"| Uptime | **{uptime}%** |",
        f"| Degraded | {degraded} |",
        f"| Down | {down} |",
    ]

    tier_summary = data.get("tier_summary", {})
    for tier_name, info in tier_summary.items():
        lines.append(f"| {tier_name.title()} Tier | {info.get('healthy', 0)}/{info.get('total', 0)} |")

    return "\n".join(lines)


def handle_services() -> str:
    data = api_get("/api/v1/status")
    if "error" in data:
        return f"❌ Error: {data['error']}"

    services = data.get("services", [])
    lines = ["| # | Service | Status | Tier | Latency |", "|---|---------|--------|------|---------|"]
    status_emoji = {"healthy": "🟢", "degraded": "🟡", "down": "🔴", "unknown": "⚪"}

    for s in services:
        emoji = status_emoji.get(s["status"], "⚪")
        lines.append(f"| {s['id']} | {s['name']} | {emoji} {s['status']} | {s['tier']} | {s['latency_ms']}ms |")

    return "\n".join(lines)


def handle_health(target: str) -> str:
    data = api_get(f"/api/v1/status/name/{target}")
    if "error" in data:
        return f"❌ Service '{target}' not found"

    status_emoji = {"healthy": "🟢", "degraded": "🟡", "down": "🔴", "unknown": "⚪"}
    emoji = status_emoji.get(data.get("status", ""), "⚪")

    return (
        f"## {emoji} {data.get('name', target)}\n"
        f"- **Status**: {data.get('status', 'unknown')}\n"
        f"- **Tier**: {data.get('tier', 'unknown')}\n"
        f"- **Latency**: {data.get('latency_ms', 0)}ms\n"
        f"- **Message**: {data.get('message', '')}\n"
        f"- **Checked**: {data.get('checked_at', '')[:19]}"
    )


def handle_restart(target: str) -> str:
    data = api_post("/api/v1/action/restart", {"target": target})
    if "error" in data:
        return f"❌ Restart failed: {data['error']}"
    return f"🔄 Restarting **{target}** ({data.get('container', '')})"


def handle_backup(target: str | None) -> str:
    data = api_post("/api/v1/action/backup", {"target": target or "all"})
    if "error" in data:
        return f"❌ Backup failed: {data['error']}"
    return f"💾 Backup triggered for **{target or 'all services'}**"


def handle_deploy(target: str) -> str:
    data = api_post("/api/v1/action/deploy", {"target": target})
    if "error" in data:
        return f"❌ Deploy failed: {data['error']}"
    return f"🚀 Deploy triggered for **{target}**"


def handle_rotate(target: str | None) -> str:
    data = api_post("/api/v1/action/rotate-secrets", {"target": target or "all"})
    if "error" in data:
        return f"❌ Rotation failed: {data['error']}"
    return f"🔐 Secret rotation triggered for **{target or 'all secrets'}**"


def handle_search(query: str) -> str:
    data = api_get(f"/api/v1/search?q={query}")
    results = data.get("results", [])
    if not results:
        return f"🔍 No services found matching '{query}'"

    lines = [f"🔍 Search results for **{query}**:", ""]
    for r in results[:10]:
        status_emoji = {"healthy": "🟢", "degraded": "🟡", "down": "🔴"}.get(r.get("status", ""), "⚪")
        lines.append(f"- {status_emoji} **#{r['id']} {r['name']}** ({r['tier']}) — {r['description'][:60]}")

    return "\n".join(lines)


def handle_docker() -> str:
    data = api_get("/api/v1/docker/stats")
    if "error" in data:
        return f"❌ Docker stats unavailable: {data['error']}"

    return (
        f"## 🐳 Docker Host\n"
        f"- **Running**: {data.get('containers_running', 0)} containers\n"
        f"- **Stopped**: {data.get('containers_stopped', 0)} containers\n"
        f"- **Images**: {data.get('images', 0)}\n"
        f"- **CPUs**: {data.get('cpu_count', 0)}\n"
        f"- **Memory**: {data.get('memory_gb', 0)} GB\n"
        f"- **Docker**: v{data.get('docker_version', '?')}\n"
        f"- **OS**: {data.get('os', '?')}"
    )


HELP_TEXT = """## ⚛ Omni Command — ChatOps Bot

| Command | Description |
|---------|-------------|
| `!omni status` | Platform overview |
| `!omni services` | All services with status |
| `!omni health <service>` | Check specific service |
| `!omni restart <service>` | Restart a container |
| `!omni backup [service]` | Trigger backup |
| `!omni deploy <app>` | Trigger deployment |
| `!omni rotate [service]` | Rotate secrets |
| `!omni search <query>` | Search services |
| `!omni docker` | Docker host stats |
| `!omni help` | This message |

*Service names use codenames: vault, litellm, gitea, mattermost, etc.*
"""


def process_command(text: str) -> str | None:
    """Parse and execute a !omni command."""
    text = text.strip()
    if not text.startswith("!omni"):
        return None

    parts = text.split(maxsplit=2)
    cmd = parts[1] if len(parts) > 1 else "help"
    arg = parts[2] if len(parts) > 2 else None

    handlers = {
        "status": lambda: handle_status(),
        "services": lambda: handle_services(),
        "health": lambda: handle_health(arg) if arg else "Usage: `!omni health <service>`",
        "restart": lambda: handle_restart(arg) if arg else "Usage: `!omni restart <service>`",
        "backup": lambda: handle_backup(arg),
        "deploy": lambda: handle_deploy(arg) if arg else "Usage: `!omni deploy <app>`",
        "rotate": lambda: handle_rotate(arg),
        "search": lambda: handle_search(arg) if arg else "Usage: `!omni search <query>`",
        "docker": lambda: handle_docker(),
        "help": lambda: HELP_TEXT,
    }

    handler = handlers.get(cmd)
    if handler:
        return handler()
    return f"Unknown command: `{cmd}`. Type `!omni help` for available commands."


def main():
    logger.info("🤖 Omni Command Mattermost Bot starting...")

    if not MATTERMOST_TOKEN:
        logger.error("MATTERMOST_TOKEN not set — bot cannot start.")
        return

    try:
        mm.login()
        logger.info("✅ Connected to Mattermost")
    except Exception as e:
        logger.error(f"Failed to connect to Mattermost: {e}")
        logger.info("Retrying in 30s...")
        time.sleep(30)
        return main()

    me = mm.users.get_user("me")
    bot_id = me["id"]
    logger.info(f"   Bot user: {me.get('username', 'unknown')} ({bot_id})")

    # Listen for messages via WebSocket
    async def ws_handler(event):
        try:
            if event.get("event") != "posted":
                return

            post = json.loads(event["data"]["post"])
            if post.get("user_id") == bot_id:
                return  # ignore own messages

            message = post.get("message", "")
            response = process_command(message)

            if response:
                mm.posts.create_post({
                    "channel_id": post["channel_id"],
                    "message": response,
                    "root_id": post.get("root_id", post["id"]),
                })
        except Exception as e:
            logger.error(f"Error handling event: {e}")

    mm.init_websocket(ws_handler)


if __name__ == "__main__":
    main()
