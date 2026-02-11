from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details, "type": "ServiceError"},
    )


async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal server error", "details": {"message": str(exc)}, "type": type(exc).__name__},
    )


exception_handlers = {
    ServiceError: service_error_handler,
    Exception: generic_error_handler,
}
