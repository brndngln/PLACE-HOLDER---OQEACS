from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Analysis MCP Server", version="1.0.0")
requests_total = Counter("analysis_mcp_server_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-170-analysis-mcp-server", "system": 170}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-170-analysis-mcp-server"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-170-analysis-mcp-server",
        "name": "Analysis MCP Server",
        "system": 170,
        "port": int(os.getenv("SERVICE_PORT", "10170")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
