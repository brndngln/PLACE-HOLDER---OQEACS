from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from shared.auth import ClientInfo
from shared.mcp_protocol import MCPServer
from shared.utils import call_service

app = FastAPI(title="omni-mcp-orchestrator")
mcp = MCPServer("omni-mcp-orchestrator")
CALLS = Counter("mcp_orchestrator_tool_calls_total", "Tool calls", ["tool"])


@mcp.mcp_tool("platform_status", "Get platform status", {"type": "object", "properties": {}})
async def platform_status(_: dict, __: ClientInfo):
    CALLS.labels(tool="platform_status").inc()
    return call_service("http://omni-orchestrator:9500/api/v1/overview")


@mcp.mcp_tool("create_coding_task", "Create coding task", {"type": "object", "properties": {"description": {"type": "string"}, "task_type": {"type": "string"}, "complexity": {"type": "string"}, "language": {"type": "string"}}})
async def create_task(args: dict, __: ClientInfo):
    CALLS.labels(tool="create_coding_task").inc()
    return call_service("http://omni-openhands-orchestrator:3001/tasks", "POST", args)


@mcp.mcp_tool("get_task_status", "Get task status", {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]})
async def task_status(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_task_status").inc()
    return call_service(f"http://omni-openhands-orchestrator:3001/tasks/{args['task_id']}")


@mcp.mcp_tool("approve_task", "Approve task", {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]})
async def approve_task(args: dict, __: ClientInfo):
    CALLS.labels(tool="approve_task").inc()
    return call_service(f"http://omni-openhands-orchestrator:3001/tasks/{args['task_id']}/approve", "POST")


@mcp.mcp_tool("reject_task", "Reject task", {"type": "object", "properties": {"task_id": {"type": "string"}, "feedback": {"type": "string"}}, "required": ["task_id", "feedback"]})
async def reject_task(args: dict, __: ClientInfo):
    CALLS.labels(tool="reject_task").inc()
    return call_service(f"http://omni-openhands-orchestrator:3001/tasks/{args['task_id']}/reject", "POST", {"feedback": args["feedback"]})


@mcp.mcp_tool("list_services", "List services", {"type": "object", "properties": {"tier": {"type": "string", "default": "all"}}})
async def list_services(args: dict, __: ClientInfo):
    CALLS.labels(tool="list_services").inc()
    data = call_service("http://omni-orchestrator:9500/api/v1/status")
    tier = args.get("tier", "all")
    return [x for x in data if tier == "all" or x.get("tier") == tier]


@mcp.mcp_tool("restart_service", "Restart service", {"type": "object", "properties": {"service_name": {"type": "string"}}, "required": ["service_name"]})
async def restart_service(args: dict, __: ClientInfo):
    CALLS.labels(tool="restart_service").inc()
    return call_service("http://omni-orchestrator:9500/api/v1/action/restart", "POST", {"container": f"omni-{args['service_name']}"})


@mcp.mcp_tool("deploy_application", "Deploy app", {"type": "object", "properties": {"app_name": {"type": "string"}, "environment": {"type": "string"}, "version": {"type": "string"}}, "required": ["app_name", "environment"]})
async def deploy(args: dict, __: ClientInfo):
    CALLS.labels(tool="deploy_application").inc()
    return call_service("http://omni-orchestrator:9500/api/v1/action/deploy", "POST", {"app": args["app_name"], "environment": args["environment"], "version": args.get("version")})


@mcp.mcp_tool("get_pipeline_stats", "Pipeline stats", {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}})
async def pipeline_stats(_: dict, __: ClientInfo):
    CALLS.labels(tool="get_pipeline_stats").inc()
    return {"orchestrator": call_service("http://omni-orchestrator:9500/api/v1/overview")}


@mcp.mcp_tool("get_gpu_status", "GPU status", {"type": "object", "properties": {}})
async def gpu(_: dict, __: ClientInfo):
    CALLS.labels(tool="get_gpu_status").inc()
    return call_service("http://omni-model-manager:11435/gpu/status")


@mcp.mcp_tool("list_models", "List models", {"type": "object", "properties": {}})
async def models(_: dict, __: ClientInfo):
    CALLS.labels(tool="list_models").inc()
    return call_service("http://omni-model-manager:11435/models")


@mcp.mcp_resource("platform://status", "Platform Status", "Live status")
async def res_status(_: ClientInfo):
    return call_service("http://omni-orchestrator:9500/api/v1/overview")


@mcp.mcp_resource("platform://services", "Services", "Service registry")
async def res_services(_: ClientInfo):
    return call_service("http://omni-orchestrator:9500/api/v1/status")


@mcp.mcp_resource("platform://gpu", "GPU", "GPU stats")
async def res_gpu(_: ClientInfo):
    return call_service("http://omni-model-manager:11435/gpu/status")


@mcp.mcp_resource("platform://pipeline", "Pipeline", "Pipeline activity")
async def res_pipeline(_: ClientInfo):
    return call_service("http://omni-orchestrator:9500/api/v1/events/history")


@mcp.mcp_prompt("build-feature", "Build feature prompt", [{"name": "description", "required": True}, {"name": "language", "required": False}])
def p_build_feature(args: dict) -> str:
    return f"Create a feature: {args.get('description')} in {args.get('language', 'python')}"


@mcp.mcp_prompt("fix-bug", "Fix bug prompt", [{"name": "description", "required": True}, {"name": "steps", "required": False}])
def p_fix_bug(args: dict) -> str:
    return f"Fix bug: {args.get('description')} steps={args.get('steps', '')}"


@mcp.mcp_prompt("create-api", "Create API prompt", [{"name": "description", "required": True}])
def p_api(args: dict) -> str:
    return f"Create API: {args.get('description')}"


@mcp.mcp_prompt("build-webapp", "Build web app", [{"name": "description", "required": True}])
def p_web(args: dict) -> str:
    return f"Build web application: {args.get('description')}"


@mcp.mcp_prompt("build-app", "Build any app", [{"name": "description", "required": True}, {"name": "type", "required": False}])
def p_app(args: dict) -> str:
    return f"Build {args.get('type', 'application')}: {args.get('description')}"


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
