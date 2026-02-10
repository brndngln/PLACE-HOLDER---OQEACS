#!/usr/bin/env python3
"""
SYSTEM 15 — INTEGRATION HUB: Stripe Webhook Handler
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

FastAPI endpoint receiving Stripe webhooks via Nango.  Verifies signatures,
updates Crater invoices, creates Plane tickets on payment failures, and
posts to the #financial channel.

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger(service="stripe-handler", system="15", component="integration-hub")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WEBHOOK_ROUTER_URL = os.environ.get("WEBHOOK_ROUTER_URL", "http://omni-webhook-router:8066")
CRATER_URL = os.environ.get("CRATER_URL", "http://omni-crater:80")
CRATER_API_KEY = os.environ.get("CRATER_API_KEY", "")
PLANE_URL = os.environ.get("PLANE_URL", "http://omni-plane-web:3000")
PLANE_API_KEY = os.environ.get("PLANE_API_KEY", "")
PLANE_WORKSPACE = os.environ.get("PLANE_WORKSPACE", "omni-quantum")
PLANE_PROJECT = os.environ.get("PLANE_PROJECT_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
STRIPE_EVENTS = Counter("stripe_events_received_total", "Stripe events received", ["event_type"])
STRIPE_PROCESSED = Counter("stripe_events_processed_total", "Stripe events processed", ["event_type"])
STRIPE_ERRORS = Counter("stripe_handler_errors_total", "Stripe handler errors", ["event_type"])
STRIPE_LATENCY = Histogram("stripe_handler_latency_seconds", "Stripe handler processing latency")

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Omni Quantum Stripe Handler",
    version="1.0.0",
    description="System 15 — Stripe webhook handler",
)


def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature (v1 scheme).

    Stripe signatures use the ``t=<timestamp>,v1=<sig>`` format where the
    signed payload is ``<timestamp>.<body>``.
    """
    if not secret:
        return True

    try:
        parts = dict(p.split("=", 1) for p in signature.split(","))
        timestamp = parts.get("t", "")
        expected_sig = parts.get("v1", "")
        signed_payload = f"{timestamp}.".encode() + payload
        computed = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, expected_sig)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Health / Metrics
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "stripe-handler", "system": "15"}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def update_crater_invoice(
    client: httpx.AsyncClient,
    invoice_id: str,
    status: str,
) -> None:
    """Mark a Crater invoice as paid or failed."""
    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.put(
                f"{CRATER_URL}/api/v1/invoices/{invoice_id}",
                headers={"Authorization": f"Bearer {CRATER_API_KEY}"},
                json={"status": status},
                timeout=10.0,
            )
            resp.raise_for_status()
            log.info("crater_invoice_updated", invoice_id=invoice_id, status=status)
            return
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            if attempt < retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            log.error("crater_update_failed", invoice_id=invoice_id, error=str(exc))


async def create_plane_ticket(
    client: httpx.AsyncClient,
    title: str,
    description: str,
    priority: str = "high",
) -> None:
    """Create a Plane issue for payment failures."""
    if not PLANE_API_KEY or not PLANE_PROJECT:
        log.warning("plane_not_configured", msg="Skipping ticket creation")
        return

    priority_map = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.post(
                f"{PLANE_URL}/api/v1/workspaces/{PLANE_WORKSPACE}/projects/{PLANE_PROJECT}/issues/",
                headers={"X-API-Key": PLANE_API_KEY},
                json={
                    "name": title,
                    "description_html": f"<p>{description}</p>",
                    "priority": priority_map.get(priority, 1),
                    "state": "triage",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            log.info("plane_ticket_created", title=title)
            return
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            if attempt < retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            log.error("plane_ticket_failed", title=title, error=str(exc))


async def post_financial_event(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> None:
    """Forward a financial event to the webhook router."""
    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.post(
                f"{WEBHOOK_ROUTER_URL}/webhook/financial",
                json=payload,
                timeout=10.0,
            )
            resp.raise_for_status()
            return
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            if attempt < retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            log.error("financial_post_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Stripe webhook endpoint
# ---------------------------------------------------------------------------
@app.post("/webhook/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
) -> dict[str, str]:
    """Process a Stripe webhook event.

    Supported events:
        - ``payment_intent.succeeded`` — mark invoice paid + post #financial
        - ``invoice.paid`` — mark invoice paid + post #financial
        - ``invoice.payment_failed`` — create Plane ticket + alert #financial
    """
    start = time.monotonic()
    raw_body = await request.body()

    if STRIPE_WEBHOOK_SECRET and not verify_stripe_signature(raw_body, stripe_signature, STRIPE_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid Stripe signature")

    body = await request.json()
    event_type = body.get("type", "unknown")
    STRIPE_EVENTS.labels(event_type=event_type).inc()

    data_obj = body.get("data", {}).get("object", {})

    async with httpx.AsyncClient() as client:
        try:
            if event_type == "payment_intent.succeeded":
                await _handle_payment_succeeded(client, data_obj)

            elif event_type == "invoice.paid":
                await _handle_invoice_paid(client, data_obj)

            elif event_type == "invoice.payment_failed":
                await _handle_invoice_failed(client, data_obj)

            else:
                log.info("stripe_event_ignored", event_type=event_type)

            STRIPE_PROCESSED.labels(event_type=event_type).inc()

        except Exception as exc:
            STRIPE_ERRORS.labels(event_type=event_type).inc()
            log.error("stripe_event_failed", event_type=event_type, error=str(exc))
            raise

    STRIPE_LATENCY.observe(time.monotonic() - start)
    return {"status": "ok", "event": event_type}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------
async def _handle_payment_succeeded(client: httpx.AsyncClient, data: dict[str, Any]) -> None:
    """Payment intent succeeded → update Crater + post #financial."""
    amount = data.get("amount", 0) / 100  # Stripe uses cents
    currency = data.get("currency", "usd").upper()
    customer = data.get("customer", "unknown")
    invoice_id = data.get("metadata", {}).get("crater_invoice_id", "")
    description = data.get("description", "Payment received")

    log.info("payment_succeeded", amount=amount, currency=currency, customer=customer)

    if invoice_id:
        await update_crater_invoice(client, invoice_id, "paid")

    await post_financial_event(client, {
        "alert_type": "Payment Received",
        "client_name": customer,
        "invoice_number": invoice_id or "N/A",
        "currency": currency,
        "amount": f"{amount:.2f}",
        "days_overdue": "0",
        "action": "No action needed — payment confirmed",
        "summary": f"Payment of {currency} {amount:.2f} received. {description}",
    })


async def _handle_invoice_paid(client: httpx.AsyncClient, data: dict[str, Any]) -> None:
    """Invoice paid → update Crater + post #financial."""
    amount = data.get("amount_paid", 0) / 100
    currency = data.get("currency", "usd").upper()
    customer_email = data.get("customer_email", "unknown")
    invoice_number = data.get("number", data.get("id", "unknown"))
    crater_id = data.get("metadata", {}).get("crater_invoice_id", "")

    log.info("invoice_paid", invoice=invoice_number, amount=amount, customer=customer_email)

    if crater_id:
        await update_crater_invoice(client, crater_id, "paid")

    await post_financial_event(client, {
        "alert_type": "Invoice Paid",
        "client_name": customer_email,
        "invoice_number": invoice_number,
        "currency": currency,
        "amount": f"{amount:.2f}",
        "days_overdue": "0",
        "action": "No action needed — invoice fully paid",
        "summary": f"Invoice {invoice_number} paid: {currency} {amount:.2f}",
    })


async def _handle_invoice_failed(client: httpx.AsyncClient, data: dict[str, Any]) -> None:
    """Invoice payment failed → Plane ticket + alert #financial."""
    amount = data.get("amount_due", 0) / 100
    currency = data.get("currency", "usd").upper()
    customer_email = data.get("customer_email", "unknown")
    invoice_number = data.get("number", data.get("id", "unknown"))
    attempt_count = data.get("attempt_count", 1)
    next_attempt = data.get("next_payment_attempt")

    log.warning("invoice_payment_failed", invoice=invoice_number, amount=amount, attempts=attempt_count)

    # Create Plane ticket
    await create_plane_ticket(
        client,
        title=f"Payment Failed: Invoice {invoice_number} ({currency} {amount:.2f})",
        description=(
            f"Stripe payment failed for invoice {invoice_number}.\n\n"
            f"- Customer: {customer_email}\n"
            f"- Amount: {currency} {amount:.2f}\n"
            f"- Attempt: #{attempt_count}\n"
            f"- Next retry: {next_attempt or 'manual action required'}\n\n"
            f"Please follow up with the client."
        ),
        priority="high",
    )

    # Alert #financial
    await post_financial_event(client, {
        "alert_type": "Payment Failed",
        "client_name": customer_email,
        "invoice_number": invoice_number,
        "currency": currency,
        "amount": f"{amount:.2f}",
        "days_overdue": str(attempt_count),
        "action": f"Payment attempt #{attempt_count} failed. Next retry: {next_attempt or 'manual'}",
        "summary": f"Payment FAILED for invoice {invoice_number}: {currency} {amount:.2f}",
    })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8068, log_level="info")
