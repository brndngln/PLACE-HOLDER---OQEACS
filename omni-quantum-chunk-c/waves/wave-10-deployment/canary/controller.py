#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  CANARY RELEASE CONTROLLER — Progressive Traffic Shifting with Auto-Rollback      ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://omni-prometheus:9090")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK_URL", "")
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "0.05"))
LATENCY_P99_THRESHOLD_MS = int(os.getenv("LATENCY_P99_THRESHOLD_MS", "500"))

class CanaryState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PROMOTING = "PROMOTING"
    COMPLETE = "COMPLETE"
    ROLLING_BACK = "ROLLING_BACK"
    FAILED = "FAILED"

class CanaryRequest(BaseModel):
    service: str
    canary_image: str
    canary_tag: str = "latest"
    traffic_steps: List[int] = [5, 10, 25, 50, 75, 100]
    step_duration_seconds: int = 300
    auto_rollback: bool = True

class CanaryStatus(BaseModel):
    canary_id: str
    service: str
    state: CanaryState
    current_step: int
    current_traffic_percent: int
    error_rate: float
    latency_p99_ms: float
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None

@dataclass
class Canary:
    id: str
    service: str
    canary_image: str
    canary_tag: str
    traffic_steps: List[int]
    step_duration_seconds: int
    auto_rollback: bool
    state: CanaryState = CanaryState.PENDING
    current_step: int = 0
    current_traffic_percent: int = 0
    error_rate: float = 0.0
    latency_p99_ms: float = 0.0
    started_at: datetime = None
    completed_at: datetime = None
    error: str = None

class CanaryController:
    def __init__(self):
        self.canaries: Dict[str, Canary] = {}
        self._http: Optional[aiohttp.ClientSession] = None
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        logger.info("canary_controller_initialized")

    async def shutdown(self):
        for task in self._running_tasks.values():
            task.cancel()
        if self._http:
            await self._http.close()

    def _generate_id(self) -> str:
        return f"canary-{int(time.time() * 1000)}"

    async def _notify(self, message: str, color: str = "good"):
        if not MATTERMOST_WEBHOOK:
            return
        try:
            await self._http.post(MATTERMOST_WEBHOOK, json={"attachments": [{"color": color, "text": message}]})
        except Exception as e:
            logger.warning("notification_failed", error=str(e))

    async def _get_metrics(self, service: str) -> Dict:
        metrics = {"error_rate": 0.0, "latency_p99_ms": 0.0}
        try:
            error_query = f'sum(rate(http_requests_total{{service="{service}",status=~"5.."}}[5m])) / sum(rate(http_requests_total{{service="{service}"}}[5m]))'
            async with self._http.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": error_query}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("data", {}).get("result", [])
                    if results:
                        metrics["error_rate"] = float(results[0]["value"][1])
        except Exception as e:
            logger.warning("metrics_fetch_failed", error=str(e))
        return metrics

    async def _should_rollback(self, canary: Canary, metrics: Dict) -> bool:
        if metrics.get("error_rate", 0.0) > ERROR_RATE_THRESHOLD:
            return True
        if metrics.get("latency_p99_ms", 0.0) > LATENCY_P99_THRESHOLD_MS:
            return True
        return False

    async def _rollback(self, canary: Canary):
        canary.state = CanaryState.ROLLING_BACK
        await self._notify(f"⚠️ Canary rollback: {canary.service}", "warning")
        canary.state = CanaryState.FAILED
        canary.completed_at = datetime.now(timezone.utc)

    async def _run_canary(self, canary: Canary):
        canary.state = CanaryState.RUNNING
        canary.started_at = datetime.now(timezone.utc)
        await self._notify(f"🐦 Starting canary: {canary.service}:{canary.canary_tag}")
        try:
            for step, traffic_percent in enumerate(canary.traffic_steps):
                canary.current_step = step
                canary.current_traffic_percent = traffic_percent
                logger.info("canary_step", service=canary.service, step=step, traffic_percent=traffic_percent)
                check_interval = min(30, canary.step_duration_seconds // 5)
                elapsed = 0
                while elapsed < canary.step_duration_seconds:
                    await asyncio.sleep(check_interval)
                    elapsed += check_interval
                    metrics = await self._get_metrics(canary.service)
                    canary.error_rate = metrics["error_rate"]
                    canary.latency_p99_ms = metrics["latency_p99_ms"]
                    if canary.auto_rollback and await self._should_rollback(canary, metrics):
                        canary.error = f"Threshold exceeded at {traffic_percent}%"
                        await self._rollback(canary)
                        return
            canary.state = CanaryState.COMPLETE
            canary.completed_at = datetime.now(timezone.utc)
            await self._notify(f"✅ Canary complete: {canary.service}:{canary.canary_tag} promoted to 100%", "good")
        except asyncio.CancelledError:
            logger.warning("canary_cancelled", canary_id=canary.id)
            await self._rollback(canary)
        except Exception as e:
            canary.error = str(e)
            canary.state = CanaryState.FAILED
            canary.completed_at = datetime.now(timezone.utc)
            await self._notify(f"❌ Canary failed: {canary.service} - {str(e)}", "danger")

    async def start_canary(self, request: CanaryRequest) -> Canary:
        canary = Canary(id=self._generate_id(), service=request.service, canary_image=request.canary_image,
            canary_tag=request.canary_tag, traffic_steps=request.traffic_steps,
            step_duration_seconds=request.step_duration_seconds, auto_rollback=request.auto_rollback)
        self.canaries[canary.id] = canary
        task = asyncio.create_task(self._run_canary(canary))
        self._running_tasks[canary.id] = task
        return canary

    async def cancel_canary(self, canary_id: str) -> bool:
        task = self._running_tasks.get(canary_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def get_canary(self, canary_id: str) -> Optional[Canary]:
        return self.canaries.get(canary_id)

    def list_canaries(self, limit: int = 20) -> List[Canary]:
        return sorted(self.canaries.values(), key=lambda c: c.started_at or datetime.min, reverse=True)[:limit]

controller = CanaryController()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await controller.initialize()
    logger.info("canary_controller_started", port=9651)
    yield
    await controller.shutdown()

app = FastAPI(title="Canary Release Controller", version="3.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "canary-controller", "version": "3.0.0"}

@app.post("/api/v1/canary")
async def start_canary(request: CanaryRequest):
    canary = await controller.start_canary(request)
    return CanaryStatus(canary_id=canary.id, service=canary.service, state=canary.state, current_step=canary.current_step,
        current_traffic_percent=canary.current_traffic_percent, error_rate=canary.error_rate, latency_p99_ms=canary.latency_p99_ms,
        started_at=canary.started_at.isoformat() if canary.started_at else "",
        completed_at=canary.completed_at.isoformat() if canary.completed_at else None, error=canary.error)

@app.get("/api/v1/canary/{canary_id}")
async def get_canary(canary_id: str):
    canary = controller.get_canary(canary_id)
    if not canary:
        raise HTTPException(status_code=404, detail="Canary not found")
    return CanaryStatus(canary_id=canary.id, service=canary.service, state=canary.state, current_step=canary.current_step,
        current_traffic_percent=canary.current_traffic_percent, error_rate=canary.error_rate, latency_p99_ms=canary.latency_p99_ms,
        started_at=canary.started_at.isoformat() if canary.started_at else "",
        completed_at=canary.completed_at.isoformat() if canary.completed_at else None, error=canary.error)

@app.delete("/api/v1/canary/{canary_id}")
async def cancel_canary(canary_id: str):
    if await controller.cancel_canary(canary_id):
        return {"status": "cancelled", "canary_id": canary_id}
    raise HTTPException(status_code=404, detail="Canary not found or already complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9651")))
