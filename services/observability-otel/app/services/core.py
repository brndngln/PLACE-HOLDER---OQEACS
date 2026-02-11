from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from app.exceptions import ServiceError
from app.models import (
    CollectorStatus,
    InstrumentationCheckRequest,
    InstrumentationCheckResult,
    SamplingPolicy,
)


class ObservabilityCore:
    def __init__(self, data_path: str, collector_url: str, default_sampling_ratio: float) -> None:
        self._path = Path(data_path)
        self._collector_url = collector_url.rstrip("/")
        self._sampling_ratio = default_sampling_ratio

    async def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            await self._persist()
            return
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        self._sampling_ratio = float(payload.get("sampling_ratio", self._sampling_ratio))

    async def _persist(self) -> None:
        payload = {
            "sampling_ratio": self._sampling_ratio,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    async def get_sampling(self) -> SamplingPolicy:
        return SamplingPolicy(ratio=self._sampling_ratio, updated_at=datetime.now(timezone.utc))

    async def set_sampling(self, ratio: float) -> SamplingPolicy:
        if ratio < 0 or ratio > 1:
            raise ServiceError("ratio must be between 0 and 1", status_code=422, code="invalid_ratio")
        self._sampling_ratio = ratio
        await self._persist()
        return await self.get_sampling()

    async def get_pipelines(self) -> dict[str, Any]:
        return {
            "traces": {"receiver": "otlp", "exporter": "collector", "sampling_ratio": self._sampling_ratio},
            "metrics": {"receiver": "otlp", "exporter": "prometheus"},
            "logs": {"receiver": "otlp", "exporter": "collector"},
        }

    async def collector_status(self) -> CollectorStatus:
        url = f"{self._collector_url}/"
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(url)
            if response.status_code >= 400:
                return CollectorStatus(healthy=False, detail=f"status_code={response.status_code}")
            return CollectorStatus(healthy=True, detail="ok")
        except Exception as exc:
            return CollectorStatus(healthy=False, detail=str(exc))

    async def instrumentation_check(self, request: InstrumentationCheckRequest) -> InstrumentationCheckResult:
        url = request.service_url.rstrip("/") + request.endpoint
        headers = {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
        start = perf_counter()
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.request(request.method, url, headers=headers)
        latency_ms = (perf_counter() - start) * 1000.0
        return InstrumentationCheckResult(
            service_url=request.service_url,
            endpoint=request.endpoint,
            status_code=response.status_code,
            has_trace_context="traceparent" in response.request.headers,
            latency_ms=round(latency_ms, 2),
        )
