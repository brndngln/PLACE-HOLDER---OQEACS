import os
import structlog
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest
from contextlib import asynccontextmanager

logger = structlog.get_logger()
EVENTS = Counter("webhook_events_total", "Webhook events", ["event_type"])
MM_WEBHOOK = "http://omni-mattermost-webhook:8066"

PLANE_API = os.getenv("PLANE_API_BASE", "http://omni-plane-web:3000/api/v1")
PLANE_TOKEN = os.getenv("PLANE_API_TOKEN", "")
PLANE_WORKSPACE = os.getenv("PLANE_WORKSPACE", "omni-quantum")
TWENTY_API = os.getenv("TWENTY_API_BASE", "http://omni-twenty:3000/api")
TWENTY_TOKEN = os.getenv("TWENTY_API_TOKEN", "")
CRATER_API = os.getenv("CRATER_API_BASE", "http://omni-crater:80/api/v1")
CRATER_TOKEN = os.getenv("CRATER_API_TOKEN", "")
GITEA_API = os.getenv("GITEA_API_BASE", "http://omni-gitea:3000/api/v1")
GITEA_TOKEN = os.getenv("GITEA_API_TOKEN", "")
ANALYTICS_API = os.getenv("ANALYTICS_API_BASE", "http://omni-superset:8088/api/v1")

STAGE_PROBABILITY = {
    "Lead": 0.10,
    "Qualified": 0.25,
    "Proposal Sent": 0.50,
    "Negotiation": 0.75,
    "Active Project": 0.90,
    "Completed": 1.0,
    "Lost": 0.0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CRM Sync Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


async def notify_mm(channel: str, text: str):
    async with httpx.AsyncClient() as c:
        await c.post(MM_WEBHOOK, json={"channel": channel, "text": text})


async def twenty_get(path: str) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{TWENTY_API}/{path}", headers={"Authorization": f"Bearer {TWENTY_TOKEN}"})
        r.raise_for_status()
        return r.json()


async def twenty_patch(path: str, data: dict) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.patch(
            f"{TWENTY_API}/{path}",
            headers={"Authorization": f"Bearer {TWENTY_TOKEN}"},
            json=data,
        )
        r.raise_for_status()
        return r.json()


@app.post("/webhook/twenty/deal-stage")
async def handle_deal_stage(request: Request):
    payload = await request.json()
    EVENTS.labels(event_type="deal_stage_changed").inc()

    deal = payload.get("data", {})
    deal_id = deal.get("id", "")
    stage = deal.get("stage", "")
    deal_name = deal.get("name", "Unknown")
    company_name = deal.get("company", {}).get("name", "Unknown")
    total_value = deal.get("total_value", 0)

    logger.info("crm.deal_stage", deal_id=deal_id, stage=stage, deal_name=deal_name)

    if stage == "Active Project":
        # Create Plane project from Client Project template
        async with httpx.AsyncClient() as c:
            plane_resp = await c.post(
                f"{PLANE_API}/workspaces/{PLANE_WORKSPACE}/projects/",
                headers={"Authorization": f"Bearer {PLANE_TOKEN}"},
                json={
                    "name": f"{company_name} - {deal_name}",
                    "template": "Client Project",
                    "identifier": deal_name[:3].upper(),
                },
            )
            plane_project = plane_resp.json()
            plane_project_id = plane_project.get("id", "")

            # Create Gitea repo
            gitea_resp = await c.post(
                f"{GITEA_API}/orgs/omni-quantum/repos",
                headers={"Authorization": f"token {GITEA_TOKEN}"},
                json={
                    "name": deal_name.lower().replace(" ", "-"),
                    "private": True,
                    "auto_init": True,
                    "description": f"Project repo for {company_name} - {deal_name}",
                },
            )
            gitea_repo = gitea_resp.json().get("full_name", "")

            # Update deal with linked IDs
            await twenty_patch(f"deals/{deal_id}", {
                "plane_project_id": plane_project_id,
                "gitea_repo": gitea_repo,
            })

        await notify_mm(
            "#general",
            f"\U0001f680 Deal '{deal_name}' ({company_name}) activated — "
            f"Plane project: {plane_project_id}, Gitea repo: {gitea_repo}",
        )

    elif stage == "Completed":
        # Generate invoice via Crater
        async with httpx.AsyncClient() as c:
            deal_data = await twenty_get(f"deals/{deal_id}")
            deal_detail = deal_data.get("data", deal_data)

            invoice_resp = await c.post(
                f"{CRATER_API}/invoices",
                headers={"Authorization": f"Bearer {CRATER_TOKEN}"},
                json={
                    "customer_id": deal_detail.get("company", {}).get("id", ""),
                    "items": [{
                        "name": deal_name,
                        "quantity": deal_detail.get("estimated_hours", 0),
                        "price": deal_detail.get("hourly_rate", 0),
                    }],
                    "template": "standard-project",
                },
            )
            invoice = invoice_resp.json()

        await notify_mm(
            "#financial",
            f"\U0001f4b0 Deal '{deal_name}' completed — Invoice {invoice.get('invoice_number', 'N/A')} "
            f"created for ${total_value}",
        )

    elif stage == "Lost":
        reason = deal.get("lost_reason", "No reason provided")
        logger.info("crm.deal_lost", deal_id=deal_id, reason=reason)
        async with httpx.AsyncClient() as c:
            await c.post(
                f"{ANALYTICS_API}/sqllab/execute/",
                json={
                    "database_id": 1,
                    "sql": f"INSERT INTO deal_outcomes (deal_id, outcome, reason, value) "
                           f"VALUES ('{deal_id}', 'lost', '{reason}', {total_value})",
                },
            )
        await notify_mm("#general", f"\u274c Deal '{deal_name}' lost: {reason}")

    return {"status": "processed", "stage": stage}


@app.post("/webhook/twenty/deal-created")
async def handle_deal_created(request: Request):
    payload = await request.json()
    EVENTS.labels(event_type="deal_created").inc()

    deal = payload.get("data", {})
    deal_name = deal.get("name", "Unknown")
    company_name = deal.get("company", {}).get("name", "Unknown")
    total_value = deal.get("total_value", 0)

    logger.info("crm.deal_created", deal_name=deal_name, value=total_value)
    await notify_mm("#general", f"\U0001f4bc New deal: {deal_name} ({company_name}) — ${total_value:,.2f}")
    return {"status": "processed"}


@app.get("/crm/pipeline-summary")
async def pipeline_summary():
    deals_data = await twenty_get("deals")
    deals = deals_data.get("data", [])

    summary = {}
    for deal in deals:
        stage = deal.get("stage", "Unknown")
        value = deal.get("total_value", 0) or 0
        if stage not in summary:
            summary[stage] = {"count": 0, "total_value": 0}
        summary[stage]["count"] += 1
        summary[stage]["total_value"] += value

    return {"pipeline": summary, "total_deals": len(deals)}


@app.get("/crm/revenue-forecast")
async def revenue_forecast():
    deals_data = await twenty_get("deals")
    deals = deals_data.get("data", [])

    forecast = {}
    total_weighted = 0
    for deal in deals:
        stage = deal.get("stage", "Unknown")
        value = deal.get("total_value", 0) or 0
        probability = STAGE_PROBABILITY.get(stage, 0)
        weighted = value * probability
        total_weighted += weighted

        if stage not in forecast:
            forecast[stage] = {"count": 0, "total_value": 0, "probability": probability, "weighted_value": 0}
        forecast[stage]["count"] += 1
        forecast[stage]["total_value"] += value
        forecast[stage]["weighted_value"] += weighted

    return {
        "forecast_by_stage": forecast,
        "total_weighted_revenue": total_weighted,
    }
