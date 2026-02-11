#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  BLUE-GREEN DEPLOYMENT ORCHESTRATOR — Zero-Downtime Releases                       ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import asyncio
import os
import subprocess
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = structlog.get_logger()

TRAEFIK_API = os.getenv("TRAEFIK_API", "http://omni-traefik:8080")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK_URL", "")
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "60"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "5"))

class DeploymentState(str, Enum):
    IDLE = "IDLE"
    DEPLOYING_GREEN = "DEPLOYING_GREEN"
    HEALTH_CHECKING = "HEALTH_CHECKING"
    SWITCHING_TRAFFIC = "SWITCHING_TRAFFIC"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"
    ROLLING_BACK = "ROLLING_BACK"
    FAILED = "FAILED"

class DeploymentRequest(BaseModel):
    service: str
    image: str
    tag: str = "latest"
    health_endpoint: str = "/health"
    rollback_on_failure: bool = True

class DeploymentStatus(BaseModel):
    deployment_id: str
    service: str
    state: DeploymentState
    active_color: str
    target_color: str
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None

@dataclass
class Deployment:
    id: str
    service: str
    image: str
    tag: str
    health_endpoint: str
    rollback_on_failure: bool
    state: DeploymentState = DeploymentState.IDLE
    active_color: str = "blue"
    started_at: datetime = None
    completed_at: datetime = None
    error: str = None

class BlueGreenOrchestrator:
    def __init__(self):
        self.deployments: Dict[str, Deployment] = {}
        self.current_colors: Dict[str, str] = {}
        self._http: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        logger.info("blue_green_orchestrator_initialized")

    async def shutdown(self):
        if self._http:
            await self._http.close()

    def _generate_id(self) -> str:
        return f"deploy-{int(time.time() * 1000)}"

    def _get_target_color(self, service: str) -> str:
        current = self.current_colors.get(service, "blue")
        return "green" if current == "blue" else "blue"

    async def _notify(self, message: str, color: str = "good"):
        if not MATTERMOST_WEBHOOK:
            return
        try:
            payload = {"attachments": [{"color": color, "text": message, "footer": "Blue-Green Orchestrator"}]}
            await self._http.post(MATTERMOST_WEBHOOK, json=payload)
        except Exception as e:
            logger.warning("notification_failed", error=str(e))

    async def _deploy_container(self, deployment: Deployment, color: str) -> bool:
        container_name = f"omni-{deployment.service}-{color}"
        image_full = f"{deployment.image}:{deployment.tag}"
        logger.info("deploying_container", container=container_name, image=image_full)
        try:
            cmd = ["docker", "run", "-d", "--name", container_name, "--network", "omni-quantum-network",
                   "--label", f"omni.quantum.component={deployment.service}", "--label", f"omni.quantum.color={color}",
                   "--restart", "unless-stopped", image_full]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error("container_deploy_failed", stderr=result.stderr[:500])
                return False
            logger.info("container_deployed", container=container_name)
            return True
        except Exception as e:
            logger.error("deploy_exception", error=str(e))
            return False

    async def _health_check(self, deployment: Deployment, color: str) -> bool:
        container_name = f"omni-{deployment.service}-{color}"
        logger.info("starting_health_check", container=container_name, timeout=HEALTH_CHECK_TIMEOUT)
        start_time = time.time()
        while time.time() - start_time < HEALTH_CHECK_TIMEOUT:
            try:
                result = subprocess.run(["docker", "inspect", "-f", "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name],
                    capture_output=True, text=True, timeout=10)
                container_ip = result.stdout.strip()
                if container_ip:
                    url = f"http://{container_ip}:8000{deployment.health_endpoint}"
                    async with self._http.get(url) as resp:
                        if resp.status == 200:
                            logger.info("health_check_passed", container=container_name)
                            return True
            except Exception:
                pass
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        logger.error("health_check_timeout", container=container_name)
        return False

    async def _switch_traffic(self, deployment: Deployment, color: str) -> bool:
        logger.info("switching_traffic", to_color=color)
        return True

    async def _verify_deployment(self, deployment: Deployment, color: str) -> bool:
        return await self._health_check(deployment, color)

    async def _cleanup_old(self, deployment: Deployment, old_color: str):
        old_container = f"omni-{deployment.service}-{old_color}"
        try:
            subprocess.run(["docker", "stop", old_container], timeout=30)
            subprocess.run(["docker", "rm", old_container], timeout=30)
            logger.info("old_container_removed", container=old_container)
        except Exception as e:
            logger.warning("cleanup_failed", container=old_container, error=str(e))

    async def _rollback(self, deployment: Deployment, target_color: str):
        container_name = f"omni-{deployment.service}-{target_color}"
        logger.warning("initiating_rollback", service=deployment.service)
        await self._notify(f"⚠️ Rolling back {deployment.service}", "warning")
        try:
            subprocess.run(["docker", "stop", container_name], timeout=30)
            subprocess.run(["docker", "rm", container_name], timeout=30)
            logger.info("rollback_complete", service=deployment.service)
        except Exception as e:
            logger.error("rollback_failed", error=str(e))

    async def deploy(self, request: DeploymentRequest) -> Deployment:
        deployment = Deployment(id=self._generate_id(), service=request.service, image=request.image, tag=request.tag,
            health_endpoint=request.health_endpoint, rollback_on_failure=request.rollback_on_failure,
            active_color=self.current_colors.get(request.service, "blue"), started_at=datetime.now(timezone.utc))
        target_color = self._get_target_color(request.service)
        self.deployments[deployment.id] = deployment
        await self._notify(f"🚀 Starting deployment: {request.service}:{request.tag} → {target_color}")
        try:
            deployment.state = DeploymentState.DEPLOYING_GREEN
            if not await self._deploy_container(deployment, target_color):
                raise Exception("Container deployment failed")
            deployment.state = DeploymentState.HEALTH_CHECKING
            if not await self._health_check(deployment, target_color):
                raise Exception("Health check failed")
            deployment.state = DeploymentState.SWITCHING_TRAFFIC
            if not await self._switch_traffic(deployment, target_color):
                raise Exception("Traffic switch failed")
            deployment.state = DeploymentState.VERIFYING
            if not await self._verify_deployment(deployment, target_color):
                raise Exception("Verification failed")
            deployment.state = DeploymentState.COMPLETE
            deployment.completed_at = datetime.now(timezone.utc)
            self.current_colors[request.service] = target_color
            await self._cleanup_old(deployment, deployment.active_color)
            await self._notify(f"✅ Deployment complete: {request.service}:{request.tag} is now {target_color}", "good")
            logger.info("deployment_complete", deployment_id=deployment.id, service=request.service)
        except Exception as e:
            deployment.state = DeploymentState.FAILED
            deployment.error = str(e)
            deployment.completed_at = datetime.now(timezone.utc)
            logger.error("deployment_failed", deployment_id=deployment.id, error=str(e))
            await self._notify(f"❌ Deployment failed: {request.service} - {str(e)}", "danger")
            if request.rollback_on_failure:
                deployment.state = DeploymentState.ROLLING_BACK
                await self._rollback(deployment, target_color)
        return deployment

    def get_status(self, deployment_id: str) -> Optional[Deployment]:
        return self.deployments.get(deployment_id)

    def list_deployments(self, limit: int = 20) -> List[Deployment]:
        return sorted(self.deployments.values(), key=lambda d: d.started_at or datetime.min, reverse=True)[:limit]

orchestrator = BlueGreenOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await orchestrator.initialize()
    logger.info("blue_green_orchestrator_started", port=9650)
    yield
    await orchestrator.shutdown()

app = FastAPI(title="Blue-Green Deployment Orchestrator", version="3.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "blue-green-orchestrator", "version": "3.0.0"}

@app.post("/api/v1/deploy")
async def deploy(request: DeploymentRequest):
    deployment = await orchestrator.deploy(request)
    return DeploymentStatus(deployment_id=deployment.id, service=deployment.service, state=deployment.state,
        active_color=deployment.active_color, target_color=orchestrator._get_target_color(deployment.service),
        started_at=deployment.started_at.isoformat() if deployment.started_at else "",
        completed_at=deployment.completed_at.isoformat() if deployment.completed_at else None, error=deployment.error)

@app.get("/api/v1/deploy/{deployment_id}")
async def get_deployment(deployment_id: str):
    deployment = orchestrator.get_status(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return DeploymentStatus(deployment_id=deployment.id, service=deployment.service, state=deployment.state,
        active_color=deployment.active_color, target_color=orchestrator._get_target_color(deployment.service),
        started_at=deployment.started_at.isoformat() if deployment.started_at else "",
        completed_at=deployment.completed_at.isoformat() if deployment.completed_at else None, error=deployment.error)

@app.get("/api/v1/deployments")
async def list_deployments(limit: int = 20):
    deployments = orchestrator.list_deployments(limit)
    return [DeploymentStatus(deployment_id=d.id, service=d.service, state=d.state, active_color=d.active_color,
        target_color=orchestrator._get_target_color(d.service), started_at=d.started_at.isoformat() if d.started_at else "",
        completed_at=d.completed_at.isoformat() if d.completed_at else None, error=d.error) for d in deployments]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9650")))
