from __future__ import annotations

from datetime import datetime

from src.models import TraceQuery, TraceSpan
from src.services.trace_store import TraceStore


def _span(trace: str, span: str, svc: str, dur: float):
    return TraceSpan(trace_id=trace, span_id=span, service_name=svc, operation_name="op", start_time=datetime.utcnow(), duration_ms=dur, status="ok")


def test_store_and_get_trace() -> None:
    s = TraceStore()
    s.store_span(_span("t1", "s1", "svc", 10))
    assert len(s.get_trace("t1")) == 1


def test_query_by_service() -> None:
    s = TraceStore()
    s.store_span(_span("t1", "s1", "a", 10))
    s.store_span(_span("t2", "s2", "b", 20))
    out = s.query_traces(TraceQuery(service_name="a"))
    assert out.total_count == 1


def test_duration_filter() -> None:
    s = TraceStore()
    s.store_span(_span("t1", "s1", "a", 10))
    out = s.query_traces(TraceQuery(min_duration_ms=11))
    assert out.total_count == 0


def test_limit_applied() -> None:
    s = TraceStore()
    for i in range(5):
        s.store_span(_span(f"t{i}", f"s{i}", "a", 1))
    out = s.query_traces(TraceQuery(limit=2))
    assert len(out.traces) <= 2
