from __future__ import annotations

import asyncio
import csv
import hmac
import io
import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

import asyncpg
import httpx
import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

EVENTS_TOTAL = Counter("audit_events_total", "Total audit events", ["event_type", "action", "success"])
BUFFER_SIZE = Gauge("audit_events_buffer_size", "In-memory buffered audit events")
WRITE_LATENCY = Histogram("audit_events_write_latency_seconds", "Audit DB write latency")
QUERY_LATENCY = Histogram("audit_events_query_latency_seconds", "Audit query latency", ["endpoint"])

MAX_BUFFER = 10_000
ALERT_THRESHOLD = 8_000
FLUSH_INTERVAL_SECONDS = 5
MAX_BATCH_SIZE = 1_000


class AuditEventIn(BaseModel):
    event_type: str = Field(max_length=100)
    actor_type: Literal["user", "service", "agent", "system"]
    actor_id: str = Field(max_length=200)
    resource_type: str = Field(max_length=100)
    resource_id: str = Field(max_length=200)
    action: Literal["create", "read", "update", "delete", "approve", "reject", "deploy", "rollback"]
    details: dict[str, Any] | None = None
    source_ip: str | None = Field(default=None, max_length=45)
    trace_id: str | None = Field(default=None, max_length=100)
    success: bool = True
    error_message: str | None = None


class AuditEvent(AuditEventIn):
    id: UUID
    timestamp: datetime
    created_at: datetime


class SummaryResponse(BaseModel):
    events_per_day: list[dict[str, Any]]
    top_actors: list[dict[str, Any]]
    top_resources: list[dict[str, Any]]
    error_rate: float


class AuditStore:
    def __init__(self, database_url: str, mm_webhook: str) -> None:
        self.database_url = database_url
        self.mm_webhook = mm_webhook
        self.pool: asyncpg.Pool | None = None
        self.buffer: deque[AuditEventIn] = deque(maxlen=MAX_BUFFER)
        self._buffer_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(timeout=10.0)

    async def connect_once(self) -> None:
        self.pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

    async def connect_with_backoff(self, retries: int = 0, delay_seconds: float = 2.0) -> None:
        attempt = 0
        while retries == 0 or attempt < retries:
            attempt += 1
            try:
                await self.connect_once()
                logger.info("audit_db_connected", attempt=attempt)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("audit_db_connect_retry", attempt=attempt, error=str(exc))
                await asyncio.sleep(min(delay_seconds * attempt, 30.0))

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
        await self._http.aclose()

    async def alert(self, text: str) -> None:
        try:
            await self._http.post(self.mm_webhook, json={"text": text})
        except Exception as exc:  # noqa: BLE001
            logger.warning("alert_send_failed", error=str(exc))

    async def _insert_row(self, conn: asyncpg.Connection, event: AuditEventIn) -> UUID:
        query = """
            INSERT INTO audit_events (
                event_type, actor_type, actor_id, resource_type, resource_id,
                action, details, source_ip, trace_id, success, error_message
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING id
        """
        return await conn.fetchval(
            query,
            event.event_type,
            event.actor_type,
            event.actor_id,
            event.resource_type,
            event.resource_id,
            event.action,
            event.details,
            event.source_ip,
            event.trace_id,
            event.success,
            event.error_message,
        )

    async def write_event(self, event: AuditEventIn) -> UUID | None:
        start = time.perf_counter()
        try:
            if not self.pool:
                raise RuntimeError("db pool not initialized")
            async with self.pool.acquire() as conn:
                event_id = await self._insert_row(conn, event)
            EVENTS_TOTAL.labels(event_type=event.event_type, action=event.action, success=str(event.success).lower()).inc()
            return event_id
        except Exception as exc:  # noqa: BLE001
            logger.error("audit_write_failed", error=str(exc))
            await self.push_buffer(event)
            return None
        finally:
            WRITE_LATENCY.observe(time.perf_counter() - start)

    async def write_batch(self, events: list[AuditEventIn]) -> list[UUID]:
        if not self.pool:
            raise RuntimeError("db pool not initialized")
        event_ids: list[UUID] = []
        start = time.perf_counter()
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for event in events:
                        event_ids.append(await self._insert_row(conn, event))
                        EVENTS_TOTAL.labels(event_type=event.event_type, action=event.action, success=str(event.success).lower()).inc()
            return event_ids
        except Exception as exc:  # noqa: BLE001
            logger.error("audit_batch_write_failed", error=str(exc), size=len(events))
            for event in events:
                await self.push_buffer(event)
            return []
        finally:
            WRITE_LATENCY.observe(time.perf_counter() - start)

    async def push_buffer(self, event: AuditEventIn) -> None:
        async with self._buffer_lock:
            if len(self.buffer) >= MAX_BUFFER:
                self.buffer.popleft()
                await self.alert(":rotating_light: [omni-audit-logger] EMERGENCY: buffer full (10k), dropping oldest event")
            self.buffer.append(event)
            size = len(self.buffer)
            BUFFER_SIZE.set(size)
            if size >= ALERT_THRESHOLD:
                await self.alert(f":warning: [omni-audit-logger] CRITICAL buffer level {size}/{MAX_BUFFER}")

    async def flush_buffer(self) -> int:
        async with self._buffer_lock:
            if not self.buffer:
                BUFFER_SIZE.set(0)
                return 0
            pending = list(self.buffer)
            self.buffer.clear()
            BUFFER_SIZE.set(0)

        persisted = await self.write_batch(pending)
        recovered = len(persisted)
        if recovered < len(pending):
            logger.warning("buffer_flush_partial", recovered=recovered, dropped=(len(pending) - recovered))
        if recovered:
            logger.info("buffer_flush_recovered", recovered_count=recovered)
        return recovered


app = FastAPI(title="Omni Audit Logger", version="1.2.0")
store = AuditStore(
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/audit_logger"),
    os.getenv("MM_WEBHOOK", "http://omni-mattermost-webhook:8066/hooks/omni-alerts"),
)
AUDIT_API_KEY = os.getenv("AUDIT_API_KEY", "")
ALLOW_INSECURE_UNAUTH = os.getenv("ALLOW_INSECURE_UNAUTH", "false").lower() == "true"


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not AUDIT_API_KEY and not ALLOW_INSECURE_UNAUTH:
        raise HTTPException(status_code=503, detail="audit api key not configured")
    if AUDIT_API_KEY and (not x_api_key or not hmac.compare_digest(x_api_key, AUDIT_API_KEY)):
        raise HTTPException(status_code=401, detail="invalid api key")


@app.on_event("startup")
async def startup() -> None:
    async def db_connector() -> None:
        await store.connect_with_backoff(retries=0)

    async def flusher() -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
            try:
                await store.flush_buffer()
            except Exception as exc:  # noqa: BLE001
                logger.error("flush_loop_error", error=str(exc))

    asyncio.create_task(db_connector())
    asyncio.create_task(flusher())


@app.on_event("shutdown")
async def shutdown() -> None:
    await store.close()


@app.post("/events")
async def create_event(payload: AuditEventIn, request: Request, _: None = Depends(require_api_key)) -> dict[str, Any]:
    event = payload.model_copy(update={"source_ip": payload.source_ip or (request.client.host if request.client else None)})
    event_id = await store.write_event(event)
    return {"accepted": True, "event_id": str(event_id) if event_id else None, "buffered": event_id is None}


@app.post("/events/batch")
async def create_event_batch(payload: list[AuditEventIn], _: None = Depends(require_api_key)) -> dict[str, Any]:
    if len(payload) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"batch exceeds max size {MAX_BATCH_SIZE}")
    event_ids = await store.write_batch(payload)
    return {"accepted": True, "event_ids": [str(i) for i in event_ids], "count": len(event_ids)}


@app.get("/events", response_model=list[AuditEvent])
async def query_events(
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    event_type: str | None = None,
    action: str | None = None,
    success: bool | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_api_key),
) -> list[AuditEvent]:
    with QUERY_LATENCY.labels("events").time():
        clauses = ["1=1"]
        values: list[Any] = []
        for key, val in [
            ("actor_id", actor_id),
            ("resource_type", resource_type),
            ("resource_id", resource_id),
            ("event_type", event_type),
            ("action", action),
            ("success", success),
        ]:
            if val is not None:
                values.append(val)
                clauses.append(f"{key} = ${len(values)}")
        if start_time:
            values.append(start_time)
            clauses.append(f"timestamp >= ${len(values)}")
        if end_time:
            values.append(end_time)
            clauses.append(f"timestamp <= ${len(values)}")

        values.extend([limit, offset])
        query = f"SELECT * FROM audit_events WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC LIMIT ${len(values)-1} OFFSET ${len(values)}"
        if not store.pool:
            raise HTTPException(503, "database unavailable")
        rows = await store.pool.fetch(query, *values)
        return [AuditEvent(**dict(r)) for r in rows]


@app.get("/events/{event_id}", response_model=AuditEvent)
async def get_event(event_id: UUID, _: None = Depends(require_api_key)) -> AuditEvent:
    with QUERY_LATENCY.labels("event_by_id").time():
        if not store.pool:
            raise HTTPException(503, "database unavailable")
        row = await store.pool.fetchrow("SELECT * FROM audit_events WHERE id=$1", event_id)
        if not row:
            raise HTTPException(404, "event not found")
        return AuditEvent(**dict(row))


@app.get("/events/timeline/{resource_type}/{resource_id}", response_model=list[AuditEvent])
async def resource_timeline(resource_type: str, resource_id: str, _: None = Depends(require_api_key)) -> list[AuditEvent]:
    with QUERY_LATENCY.labels("resource_timeline").time():
        if not store.pool:
            raise HTTPException(503, "database unavailable")
        rows = await store.pool.fetch(
            "SELECT * FROM audit_events WHERE resource_type=$1 AND resource_id=$2 ORDER BY timestamp ASC",
            resource_type,
            resource_id,
        )
        return [AuditEvent(**dict(r)) for r in rows]


@app.get("/events/actor/{actor_id}", response_model=list[AuditEvent])
async def actor_history(actor_id: str, _: None = Depends(require_api_key)) -> list[AuditEvent]:
    with QUERY_LATENCY.labels("actor_history").time():
        if not store.pool:
            raise HTTPException(503, "database unavailable")
        rows = await store.pool.fetch("SELECT * FROM audit_events WHERE actor_id=$1 ORDER BY timestamp DESC", actor_id)
        return [AuditEvent(**dict(r)) for r in rows]


@app.get("/events/summary", response_model=SummaryResponse)
async def summary(days: int = Query(7, ge=1, le=365), _: None = Depends(require_api_key)) -> SummaryResponse:
    with QUERY_LATENCY.labels("summary").time():
        if not store.pool:
            raise HTTPException(503, "database unavailable")
        since = datetime.now(timezone.utc) - timedelta(days=days)
        per_day = await store.pool.fetch(
            "SELECT date_trunc('day', timestamp) day, event_type, COUNT(*) count FROM audit_events WHERE timestamp >= $1 GROUP BY day, event_type ORDER BY day DESC",
            since,
        )
        top_actors = await store.pool.fetch(
            "SELECT actor_id, COUNT(*) count FROM audit_events WHERE timestamp >= $1 GROUP BY actor_id ORDER BY count DESC LIMIT 10",
            since,
        )
        top_resources = await store.pool.fetch(
            "SELECT resource_type || ':' || resource_id AS resource, COUNT(*) count FROM audit_events WHERE timestamp >= $1 GROUP BY resource ORDER BY count DESC LIMIT 10",
            since,
        )
        totals = await store.pool.fetchrow(
            "SELECT COUNT(*)::float total, SUM(CASE WHEN success=false THEN 1 ELSE 0 END)::float errors FROM audit_events WHERE timestamp >= $1",
            since,
        )
        total = float(totals["total"] or 0)
        errors = float(totals["errors"] or 0)
        return SummaryResponse(
            events_per_day=[dict(r) for r in per_day],
            top_actors=[dict(r) for r in top_actors],
            top_resources=[dict(r) for r in top_resources],
            error_rate=(errors / total) if total else 0.0,
        )


@app.get("/events/export")
async def export_events(
    start: datetime,
    end: datetime,
    format: Literal["csv"] = "csv",
    _: None = Depends(require_api_key),
) -> Response:
    with QUERY_LATENCY.labels("export").time():
        if format != "csv":
            raise HTTPException(400, "only csv export is supported")
        if start > end:
            raise HTTPException(400, "start must be <= end")
        if not store.pool:
            raise HTTPException(503, "database unavailable")

        rows = await store.pool.fetch(
            "SELECT * FROM audit_events WHERE timestamp BETWEEN $1 AND $2 ORDER BY timestamp ASC",
            start,
            end,
        )
        output = io.StringIO()
        fieldnames = list(rows[0].keys()) if rows else ["id", "timestamp", "event_type"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit-events-{start.date()}-{end.date()}.csv"},
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    if not store.pool:
        raise HTTPException(503, "not ready")
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
