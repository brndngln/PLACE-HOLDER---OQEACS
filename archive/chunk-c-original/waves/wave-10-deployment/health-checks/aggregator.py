#!/usr/bin/env python3
# HEALTH CHECK AGGREGATOR — OMNI QUANTUM ELITE v3.0
import asyncio, os, time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import aiohttp, structlog
from fastapi import FastAPI
from pydantic import BaseModel
logger = structlog.get_logger()
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
CHECK_TIMEOUT = int(os.getenv("CHECK_TIMEOUT", "5"))

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"

class ServiceHealth(BaseModel):
    service: str
    status: HealthStatus
    latency_ms: int
    last_check: str
    error: Optional[str] = None

SERVICES = [
    {"name": "postgres", "url": "http://omni-postgres:5432", "type": "tcp"},
    {"name": "vault", "url": "http://omni-vault:8200/v1/sys/health"},
    {"name": "litellm", "url": "http://omni-litellm:4000/health"},
    {"name": "prometheus", "url": "http://omni-prometheus:9090/-/healthy"},
    {"name": "qdrant", "url": "http://omni-qdrant:6333/readyz"},
    {"name": "minio", "url": "http://omni-minio:9000/minio/health/live"},
    {"name": "redis", "url": "http://omni-redis:6379", "type": "tcp"},
    {"name": "orchestrator", "url": "http://omni-orchestrator:9500/health"},
]

class HealthAggregator:
    def __init__(self):
        self.results: Dict[str, ServiceHealth] = {}
        self._http: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT))
        logger.info("health_aggregator_initialized")

    async def shutdown(self):
        if self._http:
            await self._http.close()

    async def _check_http(self, service: Dict) -> ServiceHealth:
        name, url = service["name"], service["url"]
        start = time.time()
        try:
            async with self._http.get(url) as resp:
                latency_ms = int((time.time() - start) * 1000)
                status = HealthStatus.HEALTHY if resp.status == 200 else HealthStatus.UNHEALTHY
                return ServiceHealth(service=name, status=status, latency_ms=latency_ms, last_check=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return ServiceHealth(service=name, status=HealthStatus.UNHEALTHY, latency_ms=int((time.time() - start) * 1000), last_check=datetime.now(timezone.utc).isoformat(), error=str(e)[:100])

    async def _check_tcp(self, service: Dict) -> ServiceHealth:
        name, url = service["name"], service["url"]
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        host, port = parsed.hostname or "localhost", parsed.port or 80
        start = time.time()
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=CHECK_TIMEOUT)
            writer.close()
            await writer.wait_closed()
            return ServiceHealth(service=name, status=HealthStatus.HEALTHY, latency_ms=int((time.time() - start) * 1000), last_check=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return ServiceHealth(service=name, status=HealthStatus.UNHEALTHY, latency_ms=int((time.time() - start) * 1000), last_check=datetime.now(timezone.utc).isoformat(), error=str(e)[:100])

    async def check_all(self) -> List[ServiceHealth]:
        tasks = [self._check_tcp(s) if s.get("type") == "tcp" else self._check_http(s) for s in SERVICES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                result = ServiceHealth(service=SERVICES[i]["name"], status=HealthStatus.UNKNOWN, latency_ms=0, last_check=datetime.now(timezone.utc).isoformat(), error=str(result)[:100])
            self.results[result.service] = result
        return list(self.results.values())

aggregator = HealthAggregator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await aggregator.initialize()
    await aggregator.check_all()
    logger.info("health_aggregator_started", port=9653)
    yield
    await aggregator.shutdown()

app = FastAPI(title="Health Check Aggregator", version="3.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "health-aggregator", "version": "3.0.0"}

@app.get("/api/v1/health")
async def get_system_health():
    services = list(aggregator.results.values())
    healthy = sum(1 for s in services if s.status == HealthStatus.HEALTHY)
    unhealthy = sum(1 for s in services if s.status == HealthStatus.UNHEALTHY)
    return {"overall": "HEALTHY" if unhealthy == 0 else "UNHEALTHY", "healthy_count": healthy, "unhealthy_count": unhealthy, "services": services}

@app.post("/api/v1/health/check")
async def trigger_check():
    return await aggregator.check_all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9653")))
