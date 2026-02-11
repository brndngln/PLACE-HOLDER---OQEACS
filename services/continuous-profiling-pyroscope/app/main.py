from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Continuous Profiling (Pyroscope)", version="1.0.0")
requests_total = Counter("continuous-profiling-pyroscope_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "continuous-profiling-pyroscope", "system": 51}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "continuous-profiling-pyroscope"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "continuous-profiling-pyroscope",
        "name": "Continuous Profiling (Pyroscope)",
        "system": 51,
        "port": int(os.getenv("SERVICE_PORT", "4040")),
        "version": "1.0.0",
    }


@app.get("/profiles")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "profiles",
        "service": "continuous-profiling-pyroscope",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
