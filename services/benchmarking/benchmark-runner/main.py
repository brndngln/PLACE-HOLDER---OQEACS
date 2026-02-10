from __future__ import annotations

import time
from pathlib import Path
from statistics import median
from typing import Any

import httpx
import structlog
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

RUNS = Counter("benchmark_runs_total", "Benchmark runs", ["service", "result"])
REGRESSIONS = Counter("benchmark_regressions_detected_total", "Regressions", ["service", "metric"])
P95 = Gauge("benchmark_latency_p95", "Latest p95 latency", ["service"])
RPS = Gauge("benchmark_throughput_rps", "Latest throughput", ["service"])

app = FastAPI(title="Benchmark Runner", version="1.1.0")
MM_WEBHOOK = "http://omni-mattermost-webhook:8066/hooks/builds"
DEFS = Path("/benchmark-definitions")

history_store: dict[str, list[dict[str, Any]]] = {}
regression_store: list[dict[str, Any]] = []


class CompareRequest(BaseModel):
    service: str
    baseline_version: str
    candidate_version: str


def _load_definition(service_name: str) -> dict[str, Any]:
    candidates = list(DEFS.glob(f"{service_name.replace('_', '-')}-benchmark.yaml"))
    aliases = {
        "omni-orchestrator": "orchestrator-benchmark.yaml",
        "omni-token-infinity": "token-infinity-benchmark.yaml",
        "omni-code-scorer": "code-scorer-benchmark.yaml",
        "omni-knowledge-ingestor": "knowledge-ingestor-benchmark.yaml",
    }
    if not candidates and aliases.get(service_name):
        f = DEFS / aliases[service_name]
        if f.exists():
            candidates = [f]
    if not candidates:
        raise HTTPException(404, f"benchmark definition for {service_name} not found")
    return yaml.safe_load(candidates[0].read_text())


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = max(int(round((p / 100) * len(values))) - 1, 0)
    return values[min(idx, len(values) - 1)]


def _probe(target: str, scenario: dict[str, Any], iterations: int = 20) -> dict[str, float]:
    samples: list[float] = []
    ok = 0
    method = scenario.get("method", "GET")
    path = scenario["path"]
    body = scenario.get("body")
    expected = int(scenario.get("expected_status", 200))

    with httpx.Client(timeout=30.0) as client:
        for _ in range(iterations):
            start = time.perf_counter()
            r = client.request(method, f"{target}{path}", json=body)
            elapsed_ms = (time.perf_counter() - start) * 1000
            samples.append(elapsed_ms)
            if r.status_code == expected:
                ok += 1

    total_seconds = max(sum(samples) / 1000, 0.001)
    throughput = ok / total_seconds
    return {
        "p50_latency_ms": median(samples),
        "p95_latency_ms": _percentile(samples, 95),
        "p99_latency_ms": _percentile(samples, 99),
        "throughput_rps": throughput,
        "memory_peak_mb": 0.0,
        "cpu_avg_pct": 0.0,
    }


def _notify(text: str) -> None:
    try:
        httpx.post(MM_WEBHOOK, json={"text": text}, timeout=10.0)
    except Exception:
        logger.warning("mattermost_notification_failed")


def _record_history(service: str, run: dict[str, Any]) -> None:
    history_store.setdefault(service, []).append(run)
    history_store[service] = history_store[service][-200:]


def _aggregate_key_metrics(metrics: list[dict[str, Any]]) -> dict[str, float]:
    p95_vals = [m["value"] for m in metrics if m["name"].endswith("p95_latency_ms")]
    rps_vals = [m["value"] for m in metrics if m["name"].endswith("throughput_rps")]
    return {
        "worst_p95": max(p95_vals) if p95_vals else 0.0,
        "worst_rps": min(rps_vals) if rps_vals else 0.0,
    }


@app.post("/benchmark/service/{service_name}")
def run_service_benchmark(service_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    definition = _load_definition(service_name)
    target = definition["target"]
    metrics: list[dict[str, Any]] = []
    failed = False

    for s in definition.get("scenarios", []):
        result = _probe(target, s)
        thr = s.get("thresholds", {})
        p95_limit = float(thr.get("p95_latency_ms", 1e9))
        min_rps = float(thr.get("min_rps", 0))
        p95_pass = result["p95_latency_ms"] <= p95_limit
        rps_pass = result["throughput_rps"] >= min_rps
        metrics.extend(
            [
                {"name": f"{s['name']}.p95_latency_ms", "value": result["p95_latency_ms"], "threshold": p95_limit, "passed": p95_pass},
                {"name": f"{s['name']}.throughput_rps", "value": result["throughput_rps"], "threshold": min_rps, "passed": rps_pass},
                {"name": f"{s['name']}.memory_peak_mb", "value": result["memory_peak_mb"], "threshold": 0, "passed": True},
                {"name": f"{s['name']}.cpu_avg_pct", "value": result["cpu_avg_pct"], "threshold": 0, "passed": True},
            ]
        )
        if not (p95_pass and rps_pass):
            failed = True
            REGRESSIONS.labels(service=service_name, metric=s["name"]).inc()
            regression_store.append({"service": service_name, "metric": s["name"], "timestamp": int(time.time())})

    status = "FAIL" if failed else "PASS"
    RUNS.labels(service=service_name, result=status).inc()
    aggregates = _aggregate_key_metrics(metrics)
    P95.labels(service=service_name).set(aggregates["worst_p95"])
    RPS.labels(service=service_name).set(aggregates["worst_rps"])

    run = {
        "status": status,
        "service": service_name,
        "version": payload.get("version"),
        "metrics": metrics,
        "timestamp": int(time.time()),
    }
    _record_history(service_name, run)
    if failed:
        _notify(f"[benchmark] regression detected for {service_name} ({payload.get('version','unknown')})")
    return run


@app.post("/benchmark/compare")
def compare_versions(payload: CompareRequest) -> dict[str, Any]:
    baseline = run_service_benchmark(payload.service, {"version": payload.baseline_version})
    candidate = run_service_benchmark(payload.service, {"version": payload.candidate_version})

    def by_name(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {i["name"]: i for i in items}

    b = by_name(baseline["metrics"])
    c = by_name(candidate["metrics"])
    deltas = []
    for k, cv in c.items():
        bv = b.get(k)
        if not bv:
            continue
        delta = cv["value"] - bv["value"]
        deltas.append({"metric": k, "baseline": bv["value"], "candidate": cv["value"], "delta": delta})

    return {"service": payload.service, "baseline": baseline, "candidate": candidate, "deltas": deltas}


@app.get("/benchmark/history/{service_name}")
def history(service_name: str) -> dict[str, Any]:
    return {"service": service_name, "history": history_store.get(service_name, [])}


@app.get("/benchmark/regressions")
def regressions() -> dict[str, Any]:
    return {"regressions": regression_store[-200:]}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
