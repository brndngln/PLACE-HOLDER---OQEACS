#!/usr/bin/env python3
# DEPLOYMENT NOTIFIER — OMNI QUANTUM ELITE v3.0
import asyncio, os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import aiohttp, structlog
from fastapi import FastAPI
from pydantic import BaseModel
logger = structlog.get_logger()
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK_URL", "")
NTFY_URL = os.getenv("NTFY_URL", "http://omni-ntfy")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "omni-deploy")
OMI_BRIDGE_URL = os.getenv("OMI_BRIDGE_URL", "http://omni-omi-bridge:9700")

class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationRequest(BaseModel):
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[str] = ["mattermost", "ntfy"]
    tags: List[str] = []
    link: Optional[str] = None

class NotificationResult(BaseModel):
    channel: str
    success: bool
    error: Optional[str] = None

class DeploymentNotifier:
    def __init__(self):
        self._http: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def shutdown(self):
        if self._http:
            await self._http.close()

    def _priority_to_color(self, p: NotificationPriority) -> str:
        return {"low": "#808080", "normal": "#00AA00", "high": "#FFA500", "urgent": "#FF0000"}.get(p.value, "#00AA00")

    async def _send_mattermost(self, req: NotificationRequest) -> NotificationResult:
        if not MATTERMOST_WEBHOOK:
            return NotificationResult(channel="mattermost", success=False, error="Not configured")
        try:
            payload = {"attachments": [{"color": self._priority_to_color(req.priority), "title": req.title, "text": req.message}]}
            async with self._http.post(MATTERMOST_WEBHOOK, json=payload) as resp:
                return NotificationResult(channel="mattermost", success=resp.status == 200, error=None if resp.status == 200 else f"HTTP {resp.status}")
        except Exception as e:
            return NotificationResult(channel="mattermost", success=False, error=str(e)[:100])

    async def _send_ntfy(self, req: NotificationRequest) -> NotificationResult:
        if not NTFY_URL:
            return NotificationResult(channel="ntfy", success=False, error="Not configured")
        try:
            headers = {"Title": req.title, "Priority": str({"low": 2, "normal": 3, "high": 4, "urgent": 5}.get(req.priority.value, 3))}
            async with self._http.post(f"{NTFY_URL}/{NTFY_TOPIC}", data=req.message, headers=headers) as resp:
                return NotificationResult(channel="ntfy", success=resp.status == 200, error=None if resp.status == 200 else f"HTTP {resp.status}")
        except Exception as e:
            return NotificationResult(channel="ntfy", success=False, error=str(e)[:100])

    async def _send_omi(self, req: NotificationRequest) -> NotificationResult:
        if not OMI_BRIDGE_URL:
            return NotificationResult(channel="omi", success=False, error="Not configured")
        try:
            pattern = {"low": "gentle", "normal": "pulse", "high": "alert", "urgent": "urgent"}.get(req.priority.value, "pulse")
            payload = {"type": "haptic", "pattern": pattern, "message": f"{req.title}: {req.message[:100]}"}
            async with self._http.post(f"{OMI_BRIDGE_URL}/api/v1/notify", json=payload) as resp:
                return NotificationResult(channel="omi", success=resp.status == 200, error=None if resp.status == 200 else f"HTTP {resp.status}")
        except Exception as e:
            return NotificationResult(channel="omi", success=False, error=str(e)[:100])

    async def notify(self, request: NotificationRequest) -> List[NotificationResult]:
        tasks = []
        for channel in request.channels:
            if channel == "mattermost":
                tasks.append(self._send_mattermost(request))
            elif channel == "ntfy":
                tasks.append(self._send_ntfy(request))
            elif channel == "omi":
                tasks.append(self._send_omi(request))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else NotificationResult(channel="unknown", success=False, error=str(r)[:100]) for r in results]

notifier = DeploymentNotifier()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await notifier.initialize()
    logger.info("notifier_started", port=9654)
    yield
    await notifier.shutdown()

app = FastAPI(title="Deployment Notifier", version="3.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "deployment-notifier", "version": "3.0.0"}

@app.post("/api/v1/notify")
async def send_notification(request: NotificationRequest):
    results = await notifier.notify(request)
    return {"results": results, "sent_at": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/notify/deploy")
async def notify_deploy(service: str, version: str, status: str, link: Optional[str] = None):
    emoji = {"success": "✅", "failure": "❌", "started": "🚀", "rollback": "🔄"}.get(status, "📦")
    priority = NotificationPriority.URGENT if status == "failure" else NotificationPriority.NORMAL
    request = NotificationRequest(title=f"{emoji} Deployment {status.title()}", message=f"Service: {service}\nVersion: {version}",
        priority=priority, channels=["mattermost", "ntfy", "omi"] if status == "failure" else ["mattermost", "ntfy"], tags=["deployment", service, status], link=link)
    return {"results": await notifier.notify(request), "sent_at": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9654")))
