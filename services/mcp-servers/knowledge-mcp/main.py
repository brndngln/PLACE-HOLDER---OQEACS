from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from shared.auth import ClientInfo
from shared.mcp_protocol import MCPServer
from shared.utils import call_service

app = FastAPI(title="omni-mcp-knowledge")
mcp = MCPServer("omni-mcp-knowledge")
CALLS = Counter("mcp_knowledge_tool_calls_total", "Tool calls", ["tool"])


@mcp.mcp_tool("search_knowledge", "Search knowledge base", {"type": "object", "properties": {"query": {"type": "string"}, "collections": {"type": "array", "items": {"type": "string"}}, "language": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["query"]})
async def search_knowledge(args: dict, __: ClientInfo):
    CALLS.labels(tool="search_knowledge").inc()
    return call_service("http://omni-meilisearch-indexer:7701/search", "POST", {"query": args["query"], "indexes": args.get("collections", ["all"]), "limit": args.get("limit", 10)})


@mcp.mcp_tool("get_design_patterns", "Design patterns", {"type": "object", "properties": {"task_description": {"type": "string"}, "language": {"type": "string", "default": "python"}}, "required": ["task_description"]})
async def design_patterns(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_design_patterns").inc()
    return call_service("http://omni-neo4j-pattern-api:7475/patterns/recommend", "POST", {"task_description": args["task_description"], "language": args.get("language", "python")})


@mcp.mcp_tool("get_anti_patterns", "Anti-patterns", {"type": "object", "properties": {"task_description": {"type": "string"}}, "required": ["task_description"]})
async def anti_patterns(args: dict, __: ClientInfo):
    CALLS.labels(tool="get_anti_patterns").inc()
    return call_service(f"http://omni-neo4j-pattern-api:7475/antipatterns/for-task?task_description={args['task_description']}")


@mcp.mcp_tool("unified_search", "Unified search", {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["query"]})
async def unified_search(args: dict, __: ClientInfo):
    CALLS.labels(tool="unified_search").inc()
    return call_service("http://omni-meilisearch-indexer:7701/search", "POST", {"query": args["query"], "indexes": ["all"], "limit": args.get("limit", 20)})


@mcp.mcp_tool("get_knowledge_stats", "Knowledge stats", {"type": "object", "properties": {}})
async def knowledge_stats(_: dict, __: ClientInfo):
    CALLS.labels(tool="get_knowledge_stats").inc()
    return {"ingest": call_service("http://omni-knowledge-ingestor:9420/ingest/stats"), "freshness": call_service("http://omni-knowledge-freshness:9430/freshness")}


@mcp.mcp_tool("ingest_source", "Ingest source", {"type": "object", "properties": {"source_type": {"type": "string"}, "url": {"type": "string"}, "name": {"type": "string"}, "category": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["source_type", "url", "name"]})
async def ingest_source(args: dict, __: ClientInfo):
    CALLS.labels(tool="ingest_source").inc()
    st = args["source_type"]
    if st == "repository":
        return call_service("http://omni-knowledge-ingestor:9420/ingest/repository", "POST", {"source_url": args["url"], "source_name": args["name"], "source_category": args.get("category", "general"), "tags": args.get("tags", [])})
    if st == "blog":
        return call_service("http://omni-knowledge-ingestor:9420/ingest/blog", "POST", {"url": args["url"], "source": args["name"], "domain": args.get("category", "general"), "tags": args.get("tags", [])})
    return {"status": "unsupported", "source_type": st}


@mcp.mcp_tool("get_freshness", "Get freshness", {"type": "object", "properties": {}})
async def freshness(_: dict, __: ClientInfo):
    CALLS.labels(tool="get_freshness").inc()
    return call_service("http://omni-knowledge-freshness:9430/freshness")


@mcp.mcp_resource("knowledge://stats", "Knowledge Stats", "Stats")
async def res_stats(_: ClientInfo):
    return await knowledge_stats({}, _)


@mcp.mcp_resource("knowledge://patterns", "Patterns", "Design patterns")
async def res_patterns(_: ClientInfo):
    return call_service("http://omni-neo4j-pattern-api:7475/patterns")


@mcp.mcp_resource("knowledge://antipatterns", "Anti-patterns", "Known anti-patterns")
async def res_anti(_: ClientInfo):
    return call_service("http://omni-neo4j-pattern-api:7475/antipatterns")


@mcp.mcp_resource("knowledge://freshness", "Freshness", "Freshness scores")
async def res_fresh(_: ClientInfo):
    return call_service("http://omni-knowledge-freshness:9430/freshness")


@mcp.mcp_resource("knowledge://collections", "Collections", "Collection inventory")
async def res_col(_: ClientInfo):
    return call_service("http://omni-knowledge-ingestor:9420/ingest/stats")


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
