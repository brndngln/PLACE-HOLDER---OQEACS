from __future__ import annotations

from collections import defaultdict

from src.models import ServiceConnection, ServiceMap, ServiceNode, TraceSpan


class ServiceMapper:
    def build_map(self, spans: list[TraceSpan]) -> ServiceMap:
        per_service: dict[str, list[TraceSpan]] = defaultdict(list)
        span_by_id = {s.span_id: s for s in spans}
        conn_data: dict[tuple[str, str], list[float]] = defaultdict(list)

        for span in spans:
            per_service[span.service_name].append(span)
            if span.parent_span_id and span.parent_span_id in span_by_id:
                parent = span_by_id[span.parent_span_id]
                if parent.service_name != span.service_name:
                    conn_data[(parent.service_name, span.service_name)].append(span.duration_ms)

        services = []
        for name, arr in per_service.items():
            avg = sum(s.duration_ms for s in arr) / max(len(arr), 1)
            err = sum(1 for s in arr if s.status.lower() not in {"ok", "success"}) / max(len(arr), 1)
            services.append(ServiceNode(name=name, span_count=len(arr), avg_latency_ms=round(avg, 2), error_rate=round(err, 3)))

        connections = []
        for (src, dst), vals in conn_data.items():
            connections.append(ServiceConnection(source=src, target=dst, request_count=len(vals), avg_latency_ms=round(sum(vals)/len(vals), 2)))

        return ServiceMap(services=sorted(services, key=lambda x: x.name), connections=connections)
