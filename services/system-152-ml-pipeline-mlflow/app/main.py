from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="ML Pipeline MLflow", version="1.0.0")
requests_total = Counter("ml_pipeline_mlflow_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-152-ml-pipeline-mlflow", "system": 152}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-152-ml-pipeline-mlflow"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-152-ml-pipeline-mlflow",
        "name": "ML Pipeline MLflow",
        "system": 152,
        "port": int(os.getenv("SERVICE_PORT", "10152")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
