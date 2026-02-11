from __future__ import annotations

from datetime import datetime

from src.models import TraceSpan
from src.services.service_mapper import ServiceMapper


def test_build_map_services() -> None:
    spans = [
        TraceSpan(trace_id="t", span_id="1", service_name="api", operation_name="x", start_time=datetime.utcnow(), duration_ms=10, status="ok"),
        TraceSpan(trace_id="t", span_id="2", parent_span_id="1", service_name="db", operation_name="q", start_time=datetime.utcnow(), duration_ms=5, status="ok"),
    ]
    m = ServiceMapper().build_map(spans)
    assert len(m.services) == 2


def test_connections_detected() -> None:
    spans = [
        TraceSpan(trace_id="t", span_id="1", service_name="api", operation_name="x", start_time=datetime.utcnow(), duration_ms=10, status="ok"),
        TraceSpan(trace_id="t", span_id="2", parent_span_id="1", service_name="db", operation_name="q", start_time=datetime.utcnow(), duration_ms=5, status="ok"),
    ]
    m = ServiceMapper().build_map(spans)
    assert m.connections


def test_error_rate() -> None:
    spans = [TraceSpan(trace_id="t", span_id="1", service_name="api", operation_name="x", start_time=datetime.utcnow(), duration_ms=10, status="error")]
    m = ServiceMapper().build_map(spans)
    assert m.services[0].error_rate == 1.0
