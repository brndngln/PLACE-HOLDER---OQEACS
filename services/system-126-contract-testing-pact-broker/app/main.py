from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Contract Testing Pact Broker", version="1.0.0")
requests_total = Counter("contract_testing_pact_broker_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-126-contract-testing-pact-broker", "system": 126}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-126-contract-testing-pact-broker"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-126-contract-testing-pact-broker",
        "name": "Contract Testing Pact Broker",
        "system": 126,
        "port": int(os.getenv("SERVICE_PORT", "10126")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
