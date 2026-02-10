from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from shared.auth import ClientInfo
from shared.mcp_protocol import MCPServer
from shared.utils import call_service

app = FastAPI(title="omni-mcp-automation")
mcp = MCPServer("omni-mcp-automation")
CALLS = Counter("mcp_automation_tool_calls_total", "Tool calls", ["tool"])


@mcp.mcp_tool("create_automation", "Create n8n automation from NL", {"type": "object", "properties": {"description": {"type": "string"}, "name": {"type": "string"}, "activate": {"type": "boolean", "default": True}}, "required": ["description"]})
async def create_automation(args: dict, __: ClientInfo):
    CALLS.labels(tool="create_automation").inc()
    # deterministic generated workflow skeleton
    workflow = {
        "name": args.get("name") or "Generated Automation",
        "nodes": [
            {"id": "trigger", "name": "Manual Trigger", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [200, 200], "parameters": {}},
            {"id": "notify", "name": "Notify", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4, "position": [500, 200], "parameters": {"method": "POST", "url": "http://omni-mattermost-webhook:8066/hooks/builds", "sendBody": True, "jsonBody": "={\"text\":\"" + args["description"] + "\"}"}},
        ],
        "connections": {"Manual Trigger": {"main": [[{"node": "Notify", "type": "main", "index": 0}]]}},
        "active": bool(args.get("activate", True)),
    }
    imported = call_service("http://omni-n8n:5678/api/v1/workflows", "POST", workflow)
    return {"status": "created", "workflow": imported, "node_count": len(workflow["nodes"]) }


@mcp.mcp_tool("list_automations", "List automations", {"type": "object", "properties": {"active": {"type": "boolean"}}})
async def list_automations(args: dict, __: ClientInfo):
    CALLS.labels(tool="list_automations").inc()
    data = call_service("http://omni-n8n:5678/api/v1/workflows")
    if "active" in args:
        return [w for w in data.get("data", []) if bool(w.get("active")) == bool(args["active"])]
    return data


@mcp.mcp_tool("get_automation_detail", "Get automation", {"type": "object", "properties": {"workflow_id": {"type": "string"}}, "required": ["workflow_id"]})
async def get_detail(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_automation_detail").inc()
    return call_service(f"http://omni-n8n:5678/api/v1/workflows/{args['workflow_id']}")


@mcp.mcp_tool("toggle_automation", "Toggle automation", {"type": "object", "properties": {"workflow_id": {"type": "string"}, "active": {"type": "boolean"}}, "required": ["workflow_id", "active"]})
async def toggle(args: dict, __: ClientInfo):
    CALLS.labels(tool="toggle_automation").inc()
    return call_service(f"http://omni-n8n:5678/api/v1/workflows/{args['workflow_id']}", "PATCH", {"active": args["active"]})


@mcp.mcp_tool("delete_automation", "Delete automation", {"type": "object", "properties": {"workflow_id": {"type": "string"}, "confirm": {"type": "boolean"}}, "required": ["workflow_id", "confirm"]})
async def delete(args: dict, __: ClientInfo):
    CALLS.labels(tool="delete_automation").inc()
    if not args["confirm"]:
        return {"status": "aborted", "reason": "confirm must be true"}
    return call_service(f"http://omni-n8n:5678/api/v1/workflows/{args['workflow_id']}", "DELETE")


@mcp.mcp_tool("get_automation_executions", "Execution history", {"type": "object", "properties": {"workflow_id": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["workflow_id"]})
async def executions(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_automation_executions").inc()
    return call_service(f"http://omni-n8n:5678/api/v1/executions?workflowId={args['workflow_id']}&limit={args.get('limit',20)}")


@mcp.mcp_prompt("create-email-automation", "Email automation", [{"name": "trigger", "required": True}, {"name": "recipients", "required": True}, {"name": "content", "required": True}])
def p_email(args: dict) -> str:
    return f"Create email automation: trigger={args.get('trigger')} recipients={args.get('recipients')} content={args.get('content')}"


@mcp.mcp_prompt("create-scheduled-automation", "Scheduled automation", [{"name": "schedule", "required": True}, {"name": "action", "required": True}])
def p_sched(args: dict) -> str:
    return f"Create scheduled automation: {args.get('schedule')} do {args.get('action')}"


@mcp.mcp_prompt("create-webhook-automation", "Webhook automation", [{"name": "source", "required": True}, {"name": "action", "required": True}])
def p_webhook(args: dict) -> str:
    return f"Create webhook automation from {args.get('source')} action {args.get('action')}"


@mcp.mcp_prompt("create-integration-automation", "Integration automation", [{"name": "source_service", "required": True}, {"name": "target_service", "required": True}, {"name": "transformation", "required": False}])
def p_integration(args: dict) -> str:
    return f"Integrate {args.get('source_service')} -> {args.get('target_service')} transform={args.get('transformation','none')}"


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
