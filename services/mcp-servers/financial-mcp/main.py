from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from shared.auth import ClientInfo
from shared.mcp_protocol import MCPServer
from shared.utils import call_service

app = FastAPI(title="omni-mcp-financial")
mcp = MCPServer("omni-mcp-financial")
CALLS = Counter("mcp_financial_tool_calls_total", "Tool calls", ["tool"])


@mcp.mcp_tool("get_financial_summary", "Financial summary", {"type": "object", "properties": {"period": {"type": "string", "default": "this_month"}}})
async def summary(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_financial_summary").inc()
    period = args.get("period", "this_month")
    return {
        "period": period,
        "invoices": call_service("http://omni-invoice-generator:81/invoices/summary"),
        "costs": call_service("http://omni-litellm-cost-tracker:4001/costs/today"),
        "pipeline": call_service("http://omni-crm-sync:3001/crm/pipeline-summary"),
    }


@mcp.mcp_tool("create_invoice", "Create invoice", {"type": "object", "properties": {"client_name": {"type": "string"}, "deal_id": {"type": "string"}, "items": {"type": "array"}, "due_days": {"type": "integer", "default": 30}, "template": {"type": "string", "default": "standard"}, "send": {"type": "boolean", "default": True}}, "required": ["client_name"]})
async def create_invoice(args: dict, __: ClientInfo):
    CALLS.labels(tool="create_invoice").inc()
    return call_service("http://omni-invoice-generator:81/generate/from-deal", "POST", args)


@mcp.mcp_tool("get_overdue_invoices", "Overdue invoices", {"type": "object", "properties": {}})
async def overdue(_: dict, __: ClientInfo):
    CALLS.labels(tool="get_overdue_invoices").inc()
    return call_service("http://omni-invoice-generator:81/invoices/overdue")


@mcp.mcp_tool("get_llm_costs", "LLM costs", {"type": "object", "properties": {"period": {"type": "string", "default": "today"}}})
async def costs(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_llm_costs").inc()
    p = args.get("period", "today")
    if p == "this_week":
        return call_service("http://omni-litellm-cost-tracker:4001/costs/this_week")
    if p == "this_month":
        return call_service("http://omni-litellm-cost-tracker:4001/costs/this_month")
    return call_service("http://omni-litellm-cost-tracker:4001/costs/today")


@mcp.mcp_tool("revenue_forecast", "Revenue forecast", {"type": "object", "properties": {}})
async def forecast(_: dict, __: ClientInfo):
    CALLS.labels(tool="revenue_forecast").inc()
    return call_service("http://omni-crm-sync:3001/crm/revenue-forecast")


@mcp.mcp_tool("get_client_summary", "Client summary", {"type": "object", "properties": {"client_name": {"type": "string"}}, "required": ["client_name"]})
async def client_summary(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_client_summary").inc()
    return {"client": args["client_name"], "pipeline": call_service("http://omni-crm-sync:3001/crm/pipeline-summary"), "invoices": call_service("http://omni-invoice-generator:81/invoices/summary")}


@mcp.mcp_tool("get_pipeline_revenue", "Pipeline revenue", {"type": "object", "properties": {"period": {"type": "string", "default": "this_month"}}})
async def pipeline_revenue(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_pipeline_revenue").inc()
    return {"period": args.get("period", "this_month"), "pipeline": call_service("http://omni-crm-sync:3001/crm/pipeline-summary"), "forecast": call_service("http://omni-crm-sync:3001/crm/revenue-forecast")}


@mcp.mcp_resource("financial://summary", "Financial Summary", "Current summary")
async def res_sum(_: ClientInfo):
    return await summary({}, _)


@mcp.mcp_resource("financial://overdue", "Overdue", "Overdue invoices")
async def res_over(_: ClientInfo):
    return call_service("http://omni-invoice-generator:81/invoices/overdue")


@mcp.mcp_resource("financial://costs", "Costs", "LLM costs")
async def res_cost(_: ClientInfo):
    return call_service("http://omni-litellm-cost-tracker:4001/costs/today")


@mcp.mcp_resource("financial://forecast", "Forecast", "Revenue forecast")
async def res_fore(_: ClientInfo):
    return call_service("http://omni-crm-sync:3001/crm/revenue-forecast")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(mcp.router)
