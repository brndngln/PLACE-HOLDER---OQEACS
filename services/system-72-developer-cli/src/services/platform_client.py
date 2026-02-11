from __future__ import annotations

import asyncio
import time

import httpx

from src.models import PlatformStatus, ServiceStatus_


class PlatformClient:
    SERVICE_REGISTRY: list[tuple[str, int]] = [
        ("debate", 9650),
        ("semantic", 9651),
        ("api-intel", 9652),
        ("exec-verify", 9653),
        ("style", 9654),
        ("test-intel", 9660),
        ("otel", 9670),
    ]

    async def get_status(self) -> PlatformStatus:
        checks = await asyncio.gather(*[self._check(name, port) for name, port in self.SERVICE_REGISTRY])
        healthy = sum(1 for c in checks if c.healthy)
        return PlatformStatus(total_services=len(checks), healthy_services=healthy, unhealthy_services=len(checks) - healthy, services=checks)

    async def _check(self, name: str, port: int) -> ServiceStatus_:
        start = time.perf_counter()
        url = f"http://localhost:{port}/health"
        healthy = False
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(url)
                healthy = resp.status_code == 200
        except Exception:
            healthy = False
        elapsed = (time.perf_counter() - start) * 1000
        return ServiceStatus_(name=name, port=port, healthy=healthy, response_time_ms=round(elapsed, 2))
