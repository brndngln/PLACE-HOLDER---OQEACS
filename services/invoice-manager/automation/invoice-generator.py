import os
import structlog
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger()
EVENTS = Counter("webhook_events_total", "Webhook events", ["event_type"])
MM_WEBHOOK = "http://omni-mattermost-webhook:8066"

TWENTY_API = os.getenv("TWENTY_API_BASE", "https://notion.so")
TWENTY_TOKEN = os.getenv("TWENTY_API_TOKEN", "")
CRATER_API = os.getenv("CRATER_API_BASE", "http://omni-crater:80/api/v1")
CRATER_TOKEN = os.getenv("CRATER_API_TOKEN", "")

TEMPLATE_MAP = {
    "web-app": "standard-project",
    "api": "standard-project",
    "mobile": "standard-project",
    "data-pipeline": "hourly-rate",
    "ai-integration": "hourly-rate",
    "full-platform": "milestone",
}

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(generate_recurring, CronTrigger(day=1, hour=9))
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Invoice Generator", lifespan=lifespan)


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


async def crater_post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{CRATER_API}/{path}",
            headers={"Authorization": f"Bearer {CRATER_TOKEN}"},
            json=data,
        )
        r.raise_for_status()
        return r.json()


async def crater_get(path: str, **params) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{CRATER_API}/{path}",
            headers={"Authorization": f"Bearer {CRATER_TOKEN}"},
            params=params,
        )
        r.raise_for_status()
        return r.json()


@app.post("/generate/from-deal")
async def generate_from_deal(request: Request):
    body = await request.json()
    deal_id = body["deal_id"]
    EVENTS.labels(event_type="generate_from_deal").inc()

    logger.info("invoice.generate_from_deal", deal_id=deal_id)

    deal_data = await twenty_get(f"deals/{deal_id}")
    deal = deal_data.get("data", deal_data)

    project_type = deal.get("project_type", "web-app")
    template = TEMPLATE_MAP.get(project_type, "standard-project")
    company = deal.get("company", {})
    customer_id = company.get("id", "")

    items = [{
        "name": deal.get("name", "Project"),
        "quantity": deal.get("estimated_hours", 0),
        "price": deal.get("hourly_rate", 0),
        "description": f"Project: {deal.get('name', '')} ({project_type})",
    }]

    invoice = await crater_post("invoices", {
        "customer_id": customer_id,
        "items": items,
        "template": template,
    })
    invoice_id = invoice.get("id", "")
    invoice_number = invoice.get("invoice_number", "N/A")

    # Send the invoice
    await crater_post(f"invoices/{invoice_id}/send", {})

    # Update deal with invoice number
    await twenty_patch(f"deals/{deal_id}", {"invoice_number": invoice_number})

    total = sum(i["quantity"] * i["price"] for i in items)
    await notify_mm(
        "#financial",
        f"\U0001f4e8 Invoice {invoice_number} generated and sent for deal {deal.get('name', '')} "
        f"({company.get('name', '')}) — ${total:,.2f} [{template}]",
    )

    return {"invoice_id": invoice_id, "invoice_number": invoice_number, "template": template}


@app.post("/generate/recurring")
async def generate_recurring_endpoint():
    result = await generate_recurring()
    return result


async def generate_recurring():
    EVENTS.labels(event_type="generate_recurring").inc()
    logger.info("invoice.generate_recurring")

    deals_data = await twenty_get("deals?filter[stage]=Active Project")
    deals = deals_data.get("data", [])

    generated = []
    for deal in deals:
        project_type = deal.get("project_type", "")
        if "retainer" not in project_type.lower() and project_type not in ("data-pipeline", "ai-integration"):
            continue

        company = deal.get("company", {})
        items = [{
            "name": f"Monthly retainer: {deal.get('name', '')}",
            "quantity": deal.get("estimated_hours", 0),
            "price": deal.get("hourly_rate", 0),
        }]

        invoice = await crater_post("invoices", {
            "customer_id": company.get("id", ""),
            "items": items,
            "template": "hourly-rate",
        })
        invoice_id = invoice.get("id", "")
        invoice_number = invoice.get("invoice_number", "N/A")

        await crater_post(f"invoices/{invoice_id}/send", {})
        await twenty_patch(f"deals/{deal['id']}", {"last_invoice": invoice_number})
        generated.append({"deal_id": deal["id"], "invoice_number": invoice_number})

    if generated:
        await notify_mm(
            "#financial",
            f"\U0001f501 Recurring invoices generated: {len(generated)} invoices sent",
        )

    logger.info("invoice.generate_recurring.done", count=len(generated))
    return {"generated": generated, "count": len(generated)}


@app.get("/invoices/summary")
async def invoices_summary():
    EVENTS.labels(event_type="invoice_summary").inc()

    all_invoices = await crater_get("invoices")
    invoices = all_invoices.get("data", [])

    total_invoiced = 0
    total_paid = 0
    total_outstanding = 0
    total_overdue = 0

    for inv in invoices:
        amount = inv.get("total", 0) or 0
        status = inv.get("status", "")
        total_invoiced += amount
        if status == "PAID":
            total_paid += amount
        elif status == "SENT":
            total_outstanding += amount
        elif status == "OVERDUE":
            total_overdue += amount
            total_outstanding += amount

    return {
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "total_overdue": total_overdue,
        "invoice_count": len(invoices),
    }
