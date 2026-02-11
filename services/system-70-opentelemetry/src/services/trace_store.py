from __future__ import annotations

from collections import defaultdict

from src.models import TraceQuery, TraceResult, TraceSpan


class TraceStore:
    def __init__(self) -> None:
        self._spans: dict[str, list[TraceSpan]] = defaultdict(list)

    def store_span(self, span: TraceSpan) -> None:
        self._spans[span.trace_id].append(span)

    def get_trace(self, trace_id: str) -> list[TraceSpan]:
        return sorted(self._spans.get(trace_id, []), key=lambda x: x.start_time)

    def query_traces(self, query: TraceQuery) -> TraceResult:
        all_spans = [s for spans in self._spans.values() for s in spans]
        filtered = []
        for span in all_spans:
            if query.service_name and span.service_name != query.service_name:
                continue
            if query.operation and span.operation_name != query.operation:
                continue
            if query.min_duration_ms is not None and span.duration_ms < query.min_duration_ms:
                continue
            if query.max_duration_ms is not None and span.duration_ms > query.max_duration_ms:
                continue
            filtered.append(span)
        filtered = sorted(filtered, key=lambda x: x.start_time, reverse=True)[: query.limit]
        return TraceResult(traces=filtered, total_count=len(filtered))
