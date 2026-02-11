from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="MCP Pipeline Server", version="1.0.0")
requests_total = Counter("mcp_pipeline_server_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-70-mcp-pipeline-server", "system": 70}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-70-mcp-pipeline-server"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-70-mcp-pipeline-server",
        "name": "MCP Pipeline Server",
        "system": 70,
        "port": int(os.getenv("SERVICE_PORT", "10070")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
