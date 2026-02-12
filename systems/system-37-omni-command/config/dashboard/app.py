"""
Omni Quantum Elite — Master Dashboard
Real-time web UI for platform-wide visibility.
"""

import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
PORT = int(os.getenv("DASHBOARD_PORT", "9501"))

app = FastAPI(title="Omni Command Dashboard")
templates = Jinja2Templates(directory="templates")


async def fetch_api(path: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(f"{ORCHESTRATOR_URL}{path}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    status_data = await fetch_api("/api/v1/status")
    overview = status_data.get("overview", {})
    services = status_data.get("services", [])
    docker_stats = await fetch_api("/api/v1/docker/stats")
    events = await fetch_api("/api/v1/events/history?limit=20")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "overview": overview,
        "services": services,
        "docker_stats": docker_stats,
        "events": events.get("events", []),
        "orchestrator_url": ORCHESTRATOR_URL,
    })


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "omni-dashboard"}
