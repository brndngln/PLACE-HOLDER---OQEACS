#!/usr/bin/env python3
"""
SYSTEM 8 — NEURAL NETWORK: Ollama Model Manager
Omni Quantum Elite AI Coding System — AI Coding Pipeline

FastAPI service (port 11435) managing model lifecycle for Ollama:
pull, load/unload, VRAM budget, priority queue, GPU monitoring,
auto-unload idle models, and benchmarking.

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client, pyyaml, pydantic
"""

import asyncio
import os
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger(service="model-manager", system="8", component="neural-network")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://omni-ollama:11434")
MATTERMOST_WEBHOOK_URL = os.environ.get("MATTERMOST_WEBHOOK_URL", "http://omni-mattermost-webhook:8066")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
CONFIG_PATH = Path(os.environ.get("MODELS_CONFIG", "/app/config/models-config.yaml"))

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ModelInfo(BaseModel):
    name: str
    status: str = "unknown"
    vram_bytes: int = 0
    vram_estimate_gb: float = 0
    load_time_seconds: float = 0
    request_count: int = 0
    error_count: int = 0
    tokens_per_second: float = 0
    context_length: int = 0
    priority: int = 99
    use_cases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    last_used: str | None = None
    loaded_at: str | None = None

class GPUStatus(BaseModel):
    vram_total_bytes: int = 0
    vram_used_bytes: int = 0
    vram_free_bytes: int = 0
    gpu_utilization_percent: float = 0
    temperature_celsius: float = 0

class PullRequest(BaseModel):
    name: str

class LoadRequest(BaseModel):
    name: str

class BenchmarkResult(BaseModel):
    model: str
    tokens_per_second: float
    total_tokens: int
    duration_seconds: float
    prompt_tokens: int
    eval_tokens: int

class JobStatus(BaseModel):
    job_id: str
    model: str
    status: str
    progress: float = 0
    error: str | None = None

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
MODEL_LOADED = Gauge("ollama_model_loaded", "Model loaded in VRAM", ["model"])
MODEL_VRAM = Gauge("ollama_model_vram_bytes", "VRAM used by model", ["model"])
MODEL_REQUESTS = Counter("ollama_model_requests_total", "Total requests per model", ["model"])
MODEL_TPS = Gauge("ollama_model_tokens_per_second", "Tokens/sec benchmark", ["model"])
MODEL_ERRORS = Counter("ollama_model_errors_total", "Errors per model", ["model"])
GPU_VRAM_TOTAL = Gauge("ollama_gpu_vram_total_bytes", "Total GPU VRAM")
GPU_VRAM_USED = Gauge("ollama_gpu_vram_used_bytes", "Used GPU VRAM")
GPU_UTIL = Gauge("ollama_gpu_utilization_percent", "GPU utilization")
GPU_TEMP = Gauge("ollama_gpu_temperature_celsius", "GPU temperature")
MODEL_LOAD_DUR = Histogram("ollama_model_load_duration_seconds", "Model load time", ["model"])

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_models_config: dict[str, Any] = {}
_model_state: dict[str, ModelInfo] = {}
_pull_jobs: dict[str, JobStatus] = {}
_load_queue: list[dict[str, Any]] = []
_loading_lock = asyncio.Lock()


def load_config() -> dict[str, Any]:
    """Load models-config.yaml."""
    global _models_config
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            _models_config = yaml.safe_load(f) or {}
    log.info("config_loaded", models=len(_models_config.get("models", [])))
    return _models_config


# ---------------------------------------------------------------------------
# Ollama API helpers
# ---------------------------------------------------------------------------
async def ollama_request(client: httpx.AsyncClient, method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Issue a request to Ollama with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.request(method, f"{OLLAMA_URL}{path}", **kwargs)
            if resp.status_code >= 500 and attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return resp
        except httpx.TransportError:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
    raise httpx.TransportError("Max retries exceeded")


async def get_ollama_models(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Get list of locally available models."""
    resp = await ollama_request(client, "GET", "/api/tags", timeout=10.0)
    resp.raise_for_status()
    return resp.json().get("models", [])


async def get_running_models(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Get currently loaded (running) models with VRAM."""
    resp = await ollama_request(client, "GET", "/api/ps", timeout=10.0)
    resp.raise_for_status()
    return resp.json().get("models", [])


async def get_gpu_status_data() -> GPUStatus:
    """Query nvidia-smi for GPU stats."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            total = int(float(parts[0])) * 1024 * 1024
            used = int(float(parts[1])) * 1024 * 1024
            free = int(float(parts[2])) * 1024 * 1024
            util = float(parts[3])
            temp = float(parts[4])
            GPU_VRAM_TOTAL.set(total)
            GPU_VRAM_USED.set(used)
            GPU_UTIL.set(util)
            GPU_TEMP.set(temp)
            return GPUStatus(vram_total_bytes=total, vram_used_bytes=used,
                             vram_free_bytes=free, gpu_utilization_percent=util,
                             temperature_celsius=temp)
    except Exception as exc:
        log.debug("nvidia_smi_unavailable", error=str(exc))
    return GPUStatus()


def _get_model_config(name: str) -> dict[str, Any]:
    """Find model in config by name."""
    for m in _models_config.get("models", []):
        if m["name"] == name or name.startswith(m["name"].split(":")[0]):
            return m
    return {}


async def _sync_model_state(client: httpx.AsyncClient) -> None:
    """Sync loaded model state from Ollama."""
    running = await get_running_models(client)
    available = await get_ollama_models(client)
    available_names = {m.get("name", m.get("model", "")) for m in available}

    loaded_names = set()
    for rm in running:
        name = rm.get("name", rm.get("model", ""))
        loaded_names.add(name)
        cfg = _get_model_config(name)
        vram = rm.get("size", rm.get("size_vram", 0))
        if name not in _model_state:
            _model_state[name] = ModelInfo(name=name)
        _model_state[name].status = "loaded"
        _model_state[name].vram_bytes = vram
        _model_state[name].priority = cfg.get("priority", 99)
        _model_state[name].context_length = cfg.get("context_length", 0)
        _model_state[name].use_cases = cfg.get("use_cases", [])
        _model_state[name].tags = cfg.get("tags", [])
        _model_state[name].vram_estimate_gb = cfg.get("vram_estimate_gb", 0)
        MODEL_LOADED.labels(model=name).set(1)
        MODEL_VRAM.labels(model=name).set(vram)

    for name in list(_model_state):
        if name not in loaded_names:
            if name in available_names:
                _model_state[name].status = "available"
            else:
                _model_state[name].status = "not_pulled"
            _model_state[name].vram_bytes = 0
            MODEL_LOADED.labels(model=name).set(0)
            MODEL_VRAM.labels(model=name).set(0)

    for cfg_model in _models_config.get("models", []):
        n = cfg_model["name"]
        if n not in _model_state:
            status = "available" if n in available_names else "not_pulled"
            _model_state[n] = ModelInfo(
                name=n, status=status, priority=cfg_model.get("priority", 99),
                context_length=cfg_model.get("context_length", 0),
                use_cases=cfg_model.get("use_cases", []),
                tags=cfg_model.get("tags", []),
                vram_estimate_gb=cfg_model.get("vram_estimate_gb", 0),
            )


async def _check_temperature_alerts() -> None:
    """Alert on high GPU temp."""
    gpu = await get_gpu_status_data()
    cfg = _models_config.get("gpu_config", {})
    crit = cfg.get("temperature_critical_celsius", 85)
    if gpu.temperature_celsius >= crit:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{MATTERMOST_WEBHOOK_URL}/webhook/prometheus", json={
                    "alerts": [{"labels": {"alertname": "GPUTemperatureCritical", "severity": "critical",
                                           "service": "neural-network"},
                                "annotations": {"summary": f"GPU temperature {gpu.temperature_celsius}°C exceeds {crit}°C"}}]
                }, timeout=5.0)
            except Exception:
                pass


async def _auto_unload_idle() -> None:
    """Unload models idle longer than threshold when VRAM is high."""
    cfg = _models_config.get("gpu_config", {})
    idle_min = cfg.get("auto_unload_idle_minutes", 120)
    gpu = await get_gpu_status_data()
    if gpu.vram_total_bytes == 0:
        return
    usage_pct = (gpu.vram_used_bytes / gpu.vram_total_bytes) * 100
    if usage_pct < 80:
        return
    now = datetime.now(tz=timezone.utc)
    for name, info in list(_model_state.items()):
        if info.status != "loaded" or not info.last_used:
            continue
        last = datetime.fromisoformat(info.last_used)
        idle_seconds = (now - last).total_seconds()
        if idle_seconds > idle_min * 60:
            log.info("auto_unloading_idle", model=name, idle_minutes=idle_seconds / 60)
            async with httpx.AsyncClient() as client:
                try:
                    await ollama_request(client, "POST", "/api/generate",
                                         json={"model": name, "keep_alive": 0}, timeout=30.0)
                except Exception:
                    pass


async def _background_monitor() -> None:
    """Background loop for health checks, temperature alerts, and auto-unload."""
    interval = _models_config.get("gpu_config", {}).get("health_check_interval_seconds", 30)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await _sync_model_state(client)
            await _check_temperature_alerts()
            await _auto_unload_idle()
        except Exception as exc:
            log.warning("background_monitor_error", error=str(exc))
        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    async with httpx.AsyncClient() as client:
        try:
            await _sync_model_state(client)
        except Exception:
            log.warning("initial_sync_failed")
    task = asyncio.create_task(_background_monitor())
    log.info("startup_complete")
    yield
    task.cancel()
    log.info("shutdown")


app = FastAPI(title="Omni Quantum Model Manager", version="1.0.0",
              description="System 8 — Neural Network model lifecycle", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness — 200 if Ollama is responsive."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await ollama_request(client, "GET", "/api/tags", timeout=5.0)
            resp.raise_for_status()
            return {"status": "ok", "service": "model-manager", "system": "8"}
        except Exception:
            raise HTTPException(503, "Ollama not responsive")


@app.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness — 200 only if at least 1 model loaded."""
    loaded = [m for m in _model_state.values() if m.status == "loaded"]
    if not loaded:
        raise HTTPException(503, detail="No models loaded")
    return {"status": "ready", "loaded_models": len(loaded)}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@app.get("/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """All models with status, VRAM, load time, request count."""
    async with httpx.AsyncClient() as client:
        await _sync_model_state(client)
    return list(_model_state.values())


@app.get("/models/{name}", response_model=ModelInfo)
async def get_model(name: str) -> ModelInfo:
    """Detail for a specific model."""
    async with httpx.AsyncClient() as client:
        await _sync_model_state(client)
    if name not in _model_state:
        raise HTTPException(404, f"Model {name} not found")
    return _model_state[name]


@app.post("/models/pull", response_model=JobStatus)
async def pull_model(req: PullRequest) -> JobStatus:
    """Pull model asynchronously, return job ID."""
    job_id = str(uuid.uuid4())
    job = JobStatus(job_id=job_id, model=req.name, status="pulling")
    _pull_jobs[job_id] = job

    async def _do_pull() -> None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await ollama_request(client, "POST", "/api/pull",
                                            json={"name": req.name, "stream": False}, timeout=1800.0)
                resp.raise_for_status()
                _pull_jobs[job_id].status = "complete"
                _pull_jobs[job_id].progress = 100
                log.info("model_pulled", model=req.name, job_id=job_id)
        except Exception as exc:
            _pull_jobs[job_id].status = "failed"
            _pull_jobs[job_id].error = str(exc)
            log.error("model_pull_failed", model=req.name, error=str(exc))
            try:
                async with httpx.AsyncClient() as c:
                    await c.post(f"{MATTERMOST_WEBHOOK_URL}/webhook/prometheus", json={
                        "alerts": [{"labels": {"alertname": "ModelPullFailure", "severity": "warning",
                                               "service": "neural-network"},
                                    "annotations": {"summary": f"Failed to pull model {req.name}: {exc}"}}]
                    }, timeout=5.0)
            except Exception:
                pass

    asyncio.create_task(_do_pull())
    return job


@app.post("/models/load", response_model=ModelInfo)
async def load_model(req: LoadRequest) -> ModelInfo:
    """Load model into VRAM with priority queue and budget check."""
    async with _loading_lock:
        gpu = await get_gpu_status_data()
        cfg = _get_model_config(req.name)
        vram_est = int(cfg.get("vram_estimate_gb", 10) * 1024 * 1024 * 1024)
        reserve_pct = _models_config.get("gpu_config", {}).get("vram_reserve_percent", 10)
        usable = int(gpu.vram_total_bytes * (1 - reserve_pct / 100))
        available = usable - gpu.vram_used_bytes

        if vram_est > available:
            loaded_by_priority = sorted(
                [m for m in _model_state.values() if m.status == "loaded"],
                key=lambda m: m.priority, reverse=True,
            )
            freed = 0
            to_unload = []
            for m in loaded_by_priority:
                if m.priority <= cfg.get("priority", 99):
                    continue
                to_unload.append(m.name)
                freed += m.vram_bytes or int(m.vram_estimate_gb * 1024 * 1024 * 1024)
                if available + freed >= vram_est:
                    break

            if available + freed < vram_est:
                raise HTTPException(507, detail={
                    "error": "Insufficient VRAM",
                    "required_bytes": vram_est,
                    "available_bytes": available,
                    "suggestion": f"Unload one of: {[m.name for m in loaded_by_priority[:3]]}",
                })

            async with httpx.AsyncClient() as client:
                for uname in to_unload:
                    log.info("evicting_for_load", evicting=uname, loading=req.name)
                    await ollama_request(client, "POST", "/api/generate",
                                         json={"model": uname, "keep_alive": 0}, timeout=30.0)

        start = time.monotonic()
        async with httpx.AsyncClient() as client:
            resp = await ollama_request(client, "POST", "/api/generate",
                                        json={"model": req.name, "prompt": "hi", "stream": False},
                                        timeout=300.0)
            resp.raise_for_status()
        load_dur = time.monotonic() - start
        MODEL_LOAD_DUR.labels(model=req.name).observe(load_dur)

        if req.name not in _model_state:
            _model_state[req.name] = ModelInfo(name=req.name)
        _model_state[req.name].status = "loaded"
        _model_state[req.name].load_time_seconds = load_dur
        _model_state[req.name].loaded_at = datetime.now(tz=timezone.utc).isoformat()
        log.info("model_loaded", model=req.name, load_time=round(load_dur, 2))
        return _model_state[req.name]


@app.post("/models/unload/{name}", response_model=ModelInfo)
async def unload_model(name: str) -> ModelInfo:
    """Unload model from VRAM."""
    async with httpx.AsyncClient() as client:
        resp = await ollama_request(client, "POST", "/api/generate",
                                    json={"model": name, "keep_alive": 0}, timeout=30.0)
        resp.raise_for_status()
    if name in _model_state:
        _model_state[name].status = "available"
        _model_state[name].vram_bytes = 0
    MODEL_LOADED.labels(model=name).set(0)
    MODEL_VRAM.labels(model=name).set(0)
    log.info("model_unloaded", model=name)
    return _model_state.get(name, ModelInfo(name=name, status="available"))


@app.get("/models/queue")
async def get_queue() -> list[dict[str, Any]]:
    """Loading queue with priorities."""
    return _load_queue


@app.get("/gpu/status", response_model=GPUStatus)
async def gpu_status() -> GPUStatus:
    """GPU VRAM total/used/free, utilization, temperature."""
    return await get_gpu_status_data()


@app.post("/models/benchmark/{name}", response_model=BenchmarkResult)
async def benchmark_model(name: str) -> BenchmarkResult:
    """Benchmark tokens/sec on a standard test prompt."""
    prompt = (
        "Write a Python function that implements binary search on a sorted list. "
        "Include type hints, docstring, and handle edge cases."
    )
    async with httpx.AsyncClient() as client:
        start = time.monotonic()
        resp = await ollama_request(client, "POST", "/api/generate",
                                    json={"model": name, "prompt": prompt, "stream": False},
                                    timeout=120.0)
        resp.raise_for_status()
        duration = time.monotonic() - start
        data = resp.json()

    eval_count = data.get("eval_count", 0)
    prompt_count = data.get("prompt_eval_count", 0)
    total = eval_count + prompt_count
    tps = eval_count / duration if duration > 0 else 0

    if name in _model_state:
        _model_state[name].tokens_per_second = round(tps, 1)
    MODEL_TPS.labels(model=name).set(tps)
    log.info("benchmark_complete", model=name, tps=round(tps, 1), duration=round(duration, 2))

    return BenchmarkResult(model=name, tokens_per_second=round(tps, 1), total_tokens=total,
                           duration_seconds=round(duration, 2), prompt_tokens=prompt_count,
                           eval_tokens=eval_count)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=11435, log_level="info")
