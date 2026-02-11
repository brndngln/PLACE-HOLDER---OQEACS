from __future__ import annotations

from fastapi import APIRouter

from src.routers.traces import store
from src.services.anomaly_detector import AnomalyDetector
from src.services.service_mapper import ServiceMapper

router = APIRouter(prefix="/api/v1", tags=["services"])


@router.get("/service-map")
def service_map():
    spans = [s for traces in store._spans.values() for s in traces]
    return ServiceMapper().build_map(spans)


@router.get("/services/{name}/latency")
def latency(name: str):
    spans = [s.duration_ms for traces in store._spans.values() for s in traces if s.service_name == name]
    anomalies = AnomalyDetector().detect_latency_anomalies(spans)
    return {"service": name, "samples": len(spans), "anomalies": anomalies}
