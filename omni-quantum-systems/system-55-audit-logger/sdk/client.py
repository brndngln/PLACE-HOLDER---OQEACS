from __future__ import annotations
from datetime import datetime
from typing import Any
import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

class AuditEvent(BaseModel):
    id: str
    event_type: str
    actor_type: str
    actor_id: str
    resource_type: str
    resource_id: str
    action: str
    details: dict[str, Any] | None = None
    trace_id: str | None = None
    success: bool = True

class AuditClient:
    def __init__(self, base_url: str):
        self._client = httpx.Client(base_url=base_url, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status();
        if r.headers.get("content-type", "").startswith("text/csv"):
            return {"content": r.content}
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: Any) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    def log(self, event_type: str, actor_type: str, actor_id: str, resource_type: str, resource_id: str, action: str, details: dict[str, Any] | None = None, trace_id: str | None = None) -> str | None:
        payload = {"event_type": event_type, "actor_type": actor_type, "actor_id": actor_id, "resource_type": resource_type, "resource_id": resource_id, "action": action, "details": details, "trace_id": trace_id}
        return self._post("/events", payload).get("event_id")

    def log_batch(self, events: list[dict[str, Any]]) -> list[str]:
        return self._post("/events/batch", events).get("event_ids", [])

    def query(self, actor_id: str | None = None, resource_type: str | None = None, event_type: str | None = None, action: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, limit: int = 100) -> list[AuditEvent]:
        data = self._client.get("/events", params={"actor_id": actor_id, "resource_type": resource_type, "event_type": event_type, "action": action, "start_time": start_time.isoformat() if start_time else None, "end_time": end_time.isoformat() if end_time else None, "limit": limit})
        data.raise_for_status()
        return [AuditEvent(**row) for row in data.json()]

    def timeline(self, resource_type: str, resource_id: str) -> list[AuditEvent]:
        return [AuditEvent(**row) for row in self._get(f"/events/timeline/{resource_type}/{resource_id}")]

    def actor_history(self, actor_id: str) -> list[AuditEvent]:
        return [AuditEvent(**row) for row in self._get(f"/events/actor/{actor_id}")]

    def summary(self, days: int = 7) -> dict[str, Any]:
        return self._get("/events/summary", days=days)

    def export(self, start: datetime, end: datetime, format: str = "csv") -> bytes:
        r = self._client.get("/events/export", params={"start": start.isoformat(), "end": end.isoformat(), "format": format})
        r.raise_for_status()
        return r.content
