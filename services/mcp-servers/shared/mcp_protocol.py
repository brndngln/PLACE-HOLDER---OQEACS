from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .auth import ClientInfo, get_client_info

logger = structlog.get_logger(__name__)

ToolFn = Callable[[dict[str, Any], ClientInfo], Awaitable[dict[str, Any]]]
ResFn = Callable[[ClientInfo], Awaitable[dict[str, Any]]]
PromptFn = Callable[[dict[str, Any]], str]


@dataclass
class MCPTool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: ToolFn


@dataclass
class MCPResource:
    uri: str
    name: str
    description: str
    mime_type: str
    fn: ResFn


@dataclass
class MCPPrompt:
    name: str
    description: str
    arguments: list[dict[str, Any]]
    fn: PromptFn


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    id: int | str | None = None
    params: dict[str, Any] = {}


class MCPServer:
    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, MCPTool] = {}
        self.resources: dict[str, MCPResource] = {}
        self.prompts: dict[str, MCPPrompt] = {}
        self.router = APIRouter()
        self._wire_routes()

    def mcp_tool(self, name: str, description: str, parameters: dict[str, Any]):
        def decorator(fn: ToolFn):
            self.tools[name] = MCPTool(name, description, parameters, fn)
            return fn

        return decorator

    def mcp_resource(self, uri: str, name: str, description: str, mime_type: str = "application/json"):
        def decorator(fn: ResFn):
            self.resources[uri] = MCPResource(uri, name, description, mime_type, fn)
            return fn

        return decorator

    def mcp_prompt(self, name: str, description: str, arguments: list[dict[str, Any]]):
        def decorator(fn: PromptFn):
            self.prompts[name] = MCPPrompt(name, description, arguments, fn)
            return fn

        return decorator

    async def _audit(self, client: ClientInfo, tool_name: str, args: dict[str, Any], result: dict[str, Any]) -> None:
        trace_id = str(uuid.uuid4())
        payload = {
            "event_type": "mcp.tool_call",
            "actor_type": "mcp_client",
            "actor_id": client.client_name,
            "resource_type": "mcp_tool",
            "resource_id": tool_name,
            "action": "execute",
            "trace_id": trace_id,
            "details": {"arguments": args, "result_summary": str(result)[:500]},
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                await c.post("http://omni-audit-logger:9550/events", json=payload)
        except Exception:
            logger.warning("audit_failed", trace_id=trace_id)

    def _ok(self, idv: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": idv, "result": result}

    def _err(self, idv: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        body: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            body["data"] = data
        return {"jsonrpc": "2.0", "id": idv, "error": body}

    async def handle_message(self, req: JsonRpcRequest, client: ClientInfo) -> dict[str, Any]:
        try:
            m = req.method
            if m == "initialize":
                return self._ok(req.id, {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self.name, "version": "1.0.0"},
                    "capabilities": {"tools": True, "resources": True, "prompts": True},
                })
            if m == "notifications/initialized":
                return self._ok(req.id, {"ack": True})
            if m == "tools/list":
                return self._ok(req.id, {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.parameters} for t in self.tools.values()]})
            if m == "tools/call":
                name = req.params.get("name")
                args = req.params.get("arguments", {})
                tool = self.tools.get(name)
                if not tool:
                    return self._err(req.id, -32601, f"Tool not found: {name}")
                out = await tool.fn(args, client)
                await self._audit(client, name, args, out)
                return self._ok(req.id, {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]})
            if m == "resources/list":
                return self._ok(req.id, {"resources": [{"uri": r.uri, "name": r.name, "description": r.description, "mimeType": r.mime_type} for r in self.resources.values()]})
            if m == "resources/read":
                uri = req.params.get("uri")
                res = self.resources.get(uri)
                if not res:
                    return self._err(req.id, -32601, f"Resource not found: {uri}")
                out = await res.fn(client)
                return self._ok(req.id, {"contents": [{"uri": uri, "mimeType": res.mime_type, "text": json.dumps(out, indent=2)}]})
            if m == "prompts/list":
                return self._ok(req.id, {"prompts": [{"name": p.name, "description": p.description, "arguments": p.arguments} for p in self.prompts.values()]})
            if m == "prompts/get":
                name = req.params.get("name")
                args = req.params.get("arguments", {})
                p = self.prompts.get(name)
                if not p:
                    return self._err(req.id, -32601, f"Prompt not found: {name}")
                text = p.fn(args)
                return self._ok(req.id, {"messages": [{"role": "user", "content": {"type": "text", "text": text}}]})
            return self._err(req.id, -32601, f"Method not found: {m}")
        except Exception as exc:
            return self._err(req.id, -32603, "Internal error", {"detail": str(exc)})

    def _wire_routes(self) -> None:
        @self.router.get("/mcp/sse")
        async def sse(_: ClientInfo = Depends(get_client_info)):
            async def events():
                while True:
                    yield {"event": "heartbeat", "data": json.dumps({"ok": True})}
                    await asyncio.sleep(30)

            return EventSourceResponse(events())

        @self.router.post("/mcp/messages")
        async def messages(req: JsonRpcRequest, client: ClientInfo = Depends(get_client_info)):
            return await self.handle_message(req, client)
