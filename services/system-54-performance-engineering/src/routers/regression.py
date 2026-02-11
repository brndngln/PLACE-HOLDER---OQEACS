from __future__ import annotations

from fastapi import APIRouter

from src.services.regression_detector import RegressionDetector

router = APIRouter(prefix="/api/v1", tags=["regression"])
_baselines: dict[str, dict[str, float]] = {}


@router.post("/regression/check")
def check(payload: dict):
    service = payload.get("service_name", "default")
    baseline = _baselines.get(service, payload.get("baseline", {}))
    current = payload.get("current", {})
    return RegressionDetector().detect_regressions(current, baseline)


@router.get("/baseline/{service_name}")
def get_baseline(service_name: str):
    return _baselines.get(service_name, {})


@router.post("/baseline/{service_name}")
def set_baseline(service_name: str, metrics: dict[str, float]):
    _baselines[service_name] = metrics
    return {"service": service_name, "baseline": metrics}
