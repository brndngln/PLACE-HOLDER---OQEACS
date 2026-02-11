from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from src.models import TraceQuery, TraceSpan
from src.services.trace_store import TraceStore

router = APIRouter(prefix="/api/v1", tags=["traces"])
store = TraceStore()


@router.get("/traces")
def traces(service_name: str | None = None, operation: str | None = None, limit: int = 100):
    q = TraceQuery(service_name=service_name, operation=operation, limit=limit)
    return store.query_traces(q)


@router.get("/traces/{trace_id}")
def trace(trace_id: str):
    return store.get_trace(trace_id)


@router.post("/traces")
def ingest(payload: dict):
    span = TraceSpan(
        trace_id=payload["trace_id"],
        span_id=payload["span_id"],
        parent_span_id=payload.get("parent_span_id"),
        service_name=payload["service_name"],
        operation_name=payload.get("operation_name", "op"),
        start_time=datetime.now(timezone.utc),
        duration_ms=float(payload.get("duration_ms", 1.0)),
        status=payload.get("status", "ok"),
        attributes=payload.get("attributes", {}),
        events=payload.get("events", []),
    )
    store.store_span(span)
    return {"status": "stored"}
