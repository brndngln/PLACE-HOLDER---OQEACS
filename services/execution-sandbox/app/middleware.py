from __future__ import annotations

from starlette.requests import Request


async def bind_request_context(request: Request) -> dict[str, str]:
    return {
        "path": request.url.path,
        "method": request.method,
        "client": request.client.host if request.client else "",
    }
