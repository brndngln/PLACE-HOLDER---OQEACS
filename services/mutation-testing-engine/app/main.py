from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Mutation Testing Engine", version="1.0.0")
requests_total = Counter("mutation-testing-engine_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "mutation-testing-engine", "system": 46}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "mutation-testing-engine"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "mutation-testing-engine",
        "name": "Mutation Testing Engine",
        "system": 46,
        "port": int(os.getenv("SERVICE_PORT", "9646")),
        "version": "1.0.0",
    }


@app.get("/mutations")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "mutations",
        "service": "mutation-testing-engine",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
