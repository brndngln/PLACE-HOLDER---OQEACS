from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Cost Tracking Dashboard", version="1.0.0")
requests_total = Counter("cost_tracking_dashboard_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-148-cost-tracking-dashboard", "system": 148}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-148-cost-tracking-dashboard"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-148-cost-tracking-dashboard",
        "name": "Cost Tracking Dashboard",
        "system": 148,
        "port": int(os.getenv("SERVICE_PORT", "10148")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
