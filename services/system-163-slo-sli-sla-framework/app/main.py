from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="SLO SLI SLA Framework", version="1.0.0")
requests_total = Counter("slo_sli_sla_framework_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-163-slo-sli-sla-framework", "system": 163}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-163-slo-sli-sla-framework"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-163-slo-sli-sla-framework",
        "name": "SLO SLI SLA Framework",
        "system": 163,
        "port": int(os.getenv("SERVICE_PORT", "10163")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
